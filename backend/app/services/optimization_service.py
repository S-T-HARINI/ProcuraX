import logging
from typing import Any, Dict, List, Optional, Protocol
from backend.app.models import (
    OptimizationRequest,
    OptimizationResponse,
    SupplierAllocation,
)
from procurax.optimizer import optimize_allocation
from procurax.scenarios import simulate_scenario

logger = logging.getLogger("procurax.backend.optimization")


class BaseOptimizationService(Protocol):
    """
    Interface Contract for Person 3 (Optimization Module).
    """
    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        ...


class OptimizationService:
    """
    Service layer bridging API requests to Person 3's optimization solver & scenario engine.
    """

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        suppliers_data = [s.model_dump() for s in request.suppliers]
        target_demand = request.target_demand
        budget = request.budget_limit

        scenario_dict = request.scenario.model_dump() if request.scenario else None

        scenario_impact_res = None
        if scenario_dict and any(scenario_dict.values()):
            # Run scenario simulation using Person 3's scenario engine
            scenario_impact_res = simulate_scenario(
                suppliers=suppliers_data,
                demand=target_demand,
                scenario=scenario_dict,
                budget=budget,
            )
            raw_opt_result = scenario_impact_res.get("scenario_summary", {})
        else:
            # Run baseline MILP optimization using Person 3's solver
            raw_opt_result = optimize_allocation(
                suppliers=suppliers_data,
                demand=target_demand,
                budget=budget,
            )

        # Parse allocations
        allocations_list: List[SupplierAllocation] = []
        for alloc in raw_opt_result.get("allocations", []):
            allocations_list.append(
                SupplierAllocation(
                    supplier_id=alloc["supplier_id"],
                    supplier_name=alloc.get("supplier_name", alloc["supplier_id"]),
                    allocated_quantity=alloc["allocated_quantity"],
                    cost_breakdown=alloc.get("cost_breakdown"),
                    capacity=alloc.get("capacity"),
                    moq=alloc.get("moq"),
                    share_of_demand_pct=alloc.get("share_of_demand_pct", 0.0),
                )
            )

        status_str = raw_opt_result.get("status", "optimal")
        is_feasible = raw_opt_result.get("is_feasible", True)
        allocated_demand = raw_opt_result.get("allocated_demand", 0)
        unmet_demand = raw_opt_result.get("unmet_demand", 0)
        total_cost = raw_opt_result.get("total_cost")
        currency = raw_opt_result.get("currency", "INR")
        budget_utilized_pct = raw_opt_result.get("budget_utilized_pct")
        unassigned = raw_opt_result.get("unassigned_suppliers", [])
        explanations = raw_opt_result.get("explanations", [])
        warnings = raw_opt_result.get("warnings", [])

        return OptimizationResponse(
            status=status_str,
            is_feasible=is_feasible,
            target_demand=target_demand,
            total_allocated_quantity=allocated_demand,
            unmet_demand=unmet_demand,
            total_landed_cost=total_cost,
            currency=currency,
            budget_limit=budget,
            budget_utilized_pct=budget_utilized_pct,
            allocations=allocations_list,
            unassigned_suppliers=unassigned,
            explanations=explanations,
            warnings=warnings,
            scenario_impact=scenario_impact_res,
            is_mock=False,
            message=f"Procurement optimization completed with status '{status_str}'.",
        )
