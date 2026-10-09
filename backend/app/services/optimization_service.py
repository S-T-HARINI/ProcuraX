from typing import Optional, Protocol
from backend.app.models import (
    OptimizationRequest,
    OptimizationResponse,
    SupplierAllocation,
    SupplierQuote,
)


class BaseOptimizationService(Protocol):
    """
    Interface Contract for Person 3 (Optimization Module).
    
    Person 3 should implement this protocol or inherit from BaseOptimizationService
    to provide advanced linear programming (e.g., PuLP / SciPy / custom optimizer).
    """
    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        ...


class OptimizationService:
    """
    Service wrapper delegating to Person 3's optimization module or mock baseline.
    """

    def __init__(self, optimizer: Optional[BaseOptimizationService] = None):
        self._optimizer = optimizer or MockOptimizationService()

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        return self._optimizer.optimize(request)


class MockOptimizationService:
    """
    Deterministic baseline solver for procurement sourcing optimization.
    Calculates landed costs, applies scenario multipliers, and allocates quantities
    respecting MOQ and supplier capacity limits.
    """

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        suppliers = request.suppliers
        target_demand = request.target_demand
        budget = request.budget_limit
        scenario = request.scenario

        price_multipliers = scenario.price_multipliers if scenario else {}
        capacity_reductions = scenario.capacity_reductions if scenario else {}

        # Pre-process supplier capabilities under scenario
        processed_suppliers = []
        total_effective_capacity = 0

        for supp in suppliers:
            # Skip suppliers missing essential numeric price or capacity
            if supp.unit_price is None or supp.unit_price <= 0:
                continue

            supplier_id = supp.supplier_id
            multiplier = price_multipliers.get(supplier_id, 1.0)
            cap_reduction_ratio = capacity_reductions.get(supplier_id, 0.0)

            eff_unit_price = supp.unit_price * multiplier
            raw_capacity = supp.capacity if (supp.capacity is not None and supp.capacity > 0) else 999999
            eff_capacity = int(raw_capacity * (1.0 - cap_reduction_ratio))
            moq = supp.moq or 0
            transport_cost = supp.transport_cost or 0.0

            processed_suppliers.append({
                "quote": supp,
                "eff_unit_price": eff_unit_price,
                "eff_capacity": eff_capacity,
                "moq": moq,
                "transport_cost": transport_cost,
            })
            total_effective_capacity += eff_capacity

        warnings = []
        if total_effective_capacity < target_demand:
            warnings.append(
                f"Infeasible demand: Total available capacity ({total_effective_capacity}) "
                f"is less than required target demand ({target_demand})."
            )

        # Sort suppliers by estimated landed cost per unit (unit price + transport allocation per unit)
        # Assuming transport cost is flat per supplier order, per-unit transport ~ transport_cost / eff_capacity
        for item in processed_suppliers:
            est_unit_transport = item["transport_cost"] / max(1, item["eff_capacity"])
            item["landed_unit_cost"] = item["eff_unit_price"] + est_unit_transport

        processed_suppliers.sort(key=lambda x: x["landed_unit_cost"])

        # Greedy allocation algorithm with MOQ enforcement
        remaining_demand = target_demand
        allocations: list[SupplierAllocation] = []
        total_landed_cost = 0.0

        for item in processed_suppliers:
            if remaining_demand <= 0:
                break

            supp: SupplierQuote = item["quote"]
            cap = item["eff_capacity"]
            moq = item["moq"]

            if cap < moq:
                # Cannot fulfill even MOQ due to capacity constraint
                continue

            # Allocation amount
            alloc_qty = min(remaining_demand, cap)

            # If alloc_qty < moq and we still need items, see if we can allocate moq
            if alloc_qty < moq:
                if cap >= moq and remaining_demand > 0:
                    alloc_qty = moq
                else:
                    continue

            unit_price = item["eff_unit_price"]
            transport_cost = item["transport_cost"]
            landed_cost_supplier = (alloc_qty * unit_price) + transport_cost
            unit_transport = transport_cost / max(1, alloc_qty)

            utilization_pct = round((alloc_qty / max(1, cap)) * 100, 2)

            allocations.append(
                SupplierAllocation(
                    supplier_id=supp.supplier_id,
                    supplier_name=supp.supplier_name,
                    allocated_quantity=alloc_qty,
                    effective_unit_price=round(unit_price, 2),
                    unit_transport_cost=round(unit_transport, 2),
                    landed_cost=round(landed_cost_supplier, 2),
                    capacity_utilization_pct=utilization_pct,
                )
            )

            total_landed_cost += landed_cost_supplier
            remaining_demand -= alloc_qty

        unmet = max(0, remaining_demand)
        status = "optimal" if unmet == 0 else "infeasible"

        budget_exceeded = False
        if budget is not None and total_landed_cost > budget:
            budget_exceeded = True
            status = "infeasible" if status == "optimal" else status
            warnings.append(
                f"Budget exceeded: Total landed cost ({round(total_landed_cost, 2)}) "
                f"exceeds specified budget limit ({budget})."
            )

        return OptimizationResponse(
            status=status,
            target_demand=target_demand,
            total_allocated_quantity=target_demand - unmet,
            total_landed_cost=round(total_landed_cost, 2),
            budget_limit=budget,
            budget_exceeded=budget_exceeded,
            allocations=allocations,
            unmet_demand=unmet,
            warnings=warnings,
            is_mock=True,
            message="Optimization solver run complete.",
        )
