"""
Task 2: Supplier Allocation Optimizer for ProcuraX.

Solves the procurement supplier allocation problem using Mixed-Integer Linear Programming (MILP).
Constraints handled:
1. Demand satisfaction: sum(q_i) == demand (or >= demand if overdelivery allowed)
2. Minimum Order Quantity (MOQ): either q_i == 0 or q_i >= moq_i
3. Supplier Capacity: q_i <= capacity_i
4. Budget: total_cost <= budget (when provided)
5. Missing or invalid supplier information: explicit exclusion tracking with reasons
6. Supplier availability: supports excluding unavailable suppliers

Returns:
- Full allocation breakdown with supplier, quantity allocated, unit price,
  transport cost, landed cost, and constraint or exclusion reasons.
"""

from typing import Any, Dict, List, Optional, Union
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from procurax.cost import calculate_landed_cost
from procurax.models import Supplier


def optimize_allocation(
    suppliers: List[Union[Dict[str, Any], Supplier]],
    demand: int,
    budget: Optional[float] = None,
    allow_overdelivery: bool = False,
    base_currency: Optional[str] = None,
    currency_rates: Optional[Dict[str, float]] = None,
    unavailable_suppliers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Optimize supplier purchase allocation to minimize total procurement landed cost.

    Args:
        suppliers: List of supplier dicts or Supplier models conforming to shared schema.
        demand: Total required purchase quantity (integer >= 0).
        budget: Maximum spending limit (optional).
        allow_overdelivery: If True, sum(q_i) >= demand is allowed when MOQ forces over-ordering.
                            Default is False (exact demand satisfaction).
        base_currency: Reference currency (defaults to currency of first supplier or INR).
        currency_rates: Currency conversion lookup for multi-currency supplier sets.
        unavailable_suppliers: List of supplier IDs to treat as unavailable/shut down.

    Returns:
        Dict conforming to OptimizationSummary schema, including full supplier_breakdown
        with constraint and exclusion reasons.
    """
    if demand < 0:
        raise ValueError(f"Demand must be non-negative: {demand}")

    # Normalize suppliers to dicts
    supplier_dicts: List[Dict[str, Any]] = []
    for s in suppliers:
        if isinstance(s, Supplier):
            supplier_dicts.append(s.model_dump())
        else:
            supplier_dicts.append(dict(s))

    warnings: List[str] = []
    explanations: List[str] = []
    unavailable_set = set(unavailable_suppliers or [])

    # Currency validation
    currencies_found = set()
    for s in supplier_dicts:
        curr = s.get("currency")
        currencies_found.add(curr or "INR")

    if not base_currency:
        base_currency = next(iter(currencies_found)) if currencies_found else "INR"

    if len(currencies_found) > 1 and not currency_rates:
        warnings.append(
            f"Multiple currencies detected {list(currencies_found)} without explicit exchange rates. "
            f"All suppliers must share a single currency or exchange rates must be provided."
        )
        return {
            "status": "infeasible",
            "is_feasible": False,
            "requested_demand": demand,
            "allocated_demand": 0,
            "unmet_demand": demand,
            "total_cost": None,
            "currency": base_currency,
            "budget": budget,
            "budget_utilized_pct": None,
            "explanations": ["Optimization halted: multiple currencies present without conversion rates."],
            "allocations": [],
            "supplier_breakdown": [
                {
                    "supplier_id": s.get("supplier_id", "UNKNOWN"),
                    "supplier_name": s.get("supplier_name", "Unknown Supplier"),
                    "allocated_quantity": 0,
                    "unit_price": s.get("unit_price"),
                    "transport_cost": s.get("transport_cost"),
                    "landed_cost": None,
                    "status": "excluded",
                    "exclusion_reason": "Currency mismatch without exchange rates",
                }
                for s in supplier_dicts
            ],
            "unassigned_suppliers": [s.get("supplier_id", "UNKNOWN") for s in supplier_dicts],
            "exclusion_reasons": {
                s.get("supplier_id", "UNKNOWN"): "Currency mismatch without exchange rates"
                for s in supplier_dicts
            },
            "warnings": warnings,
        }

    # Demand = 0 edge case
    if demand == 0:
        return {
            "status": "optimal",
            "is_feasible": True,
            "requested_demand": 0,
            "allocated_demand": 0,
            "unmet_demand": 0,
            "total_cost": 0.0,
            "currency": base_currency,
            "budget": budget,
            "budget_utilized_pct": 0.0,
            "explanations": ["Demand is 0; no suppliers allocated."],
            "allocations": [],
            "supplier_breakdown": [
                {
                    "supplier_id": s.get("supplier_id", "UNKNOWN"),
                    "supplier_name": s.get("supplier_name", "Unknown"),
                    "allocated_quantity": 0,
                    "unit_price": s.get("unit_price"),
                    "transport_cost": s.get("transport_cost"),
                    "landed_cost": 0.0,
                    "status": "unassigned",
                    "exclusion_reason": "Zero demand requested",
                }
                for s in supplier_dicts
            ],
            "unassigned_suppliers": [s.get("supplier_id", "UNKNOWN") for s in supplier_dicts],
            "exclusion_reasons": {},
            "warnings": warnings,
        }

    # Filter eligible suppliers (must have unit_price, capacity, and not be unavailable)
    eligible_suppliers: List[Dict[str, Any]] = []
    exclusion_reasons: Dict[str, str] = {}

    for s in supplier_dicts:
        sup_id = s.get("supplier_id", "UNKNOWN")
        unit_price = s.get("unit_price")
        capacity = s.get("capacity")
        moq = s.get("moq") or 1
        is_avail = s.get("is_available", True) and (s.get("available") is not False)

        missing_reasons = []
        if sup_id in unavailable_set or not is_avail:
            missing_reasons.append("supplier is marked unavailable")
        if unit_price is None:
            missing_reasons.append("unit_price is missing/null (cannot assume zero)")
        elif unit_price < 0:
            missing_reasons.append(f"negative unit_price ({unit_price})")

        if capacity is None:
            missing_reasons.append("capacity is missing/null")
        elif capacity <= 0:
            missing_reasons.append(f"capacity is non-positive ({capacity})")
        elif capacity < moq:
            missing_reasons.append(f"supplier capacity ({capacity}) is less than supplier MOQ ({moq})")

        if missing_reasons:
            reason_str = "; ".join(missing_reasons)
            exclusion_reasons[sup_id] = reason_str
            warnings.append(f"Excluded supplier {sup_id}: {reason_str}.")
        else:
            eligible_suppliers.append(s)

    # If no suppliers are eligible
    if not eligible_suppliers:
        explanations.append("No eligible suppliers available after applying data completeness and availability constraints.")
        supplier_breakdown = []
        for s in supplier_dicts:
            sid = s.get("supplier_id", "UNKNOWN")
            supplier_breakdown.append({
                "supplier_id": sid,
                "supplier_name": s.get("supplier_name", "Unknown"),
                "allocated_quantity": 0,
                "unit_price": s.get("unit_price"),
                "transport_cost": s.get("transport_cost"),
                "landed_cost": None,
                "status": "excluded",
                "exclusion_reason": exclusion_reasons.get(sid, "Ineligible"),
            })

        return {
            "status": "infeasible",
            "is_feasible": False,
            "requested_demand": demand,
            "allocated_demand": 0,
            "unmet_demand": demand,
            "total_cost": None,
            "currency": base_currency,
            "budget": budget,
            "budget_utilized_pct": None,
            "explanations": explanations,
            "allocations": [],
            "supplier_breakdown": supplier_breakdown,
            "unassigned_suppliers": [s.get("supplier_id", "UNKNOWN") for s in supplier_dicts],
            "exclusion_reasons": exclusion_reasons,
            "warnings": warnings,
        }

    N = len(eligible_suppliers)

    # Convert supplier costs to base currency and check transport cost modes
    normalized_prices = []
    normalized_transports = []
    is_per_unit_transport_flags = []
    capacities = []
    moqs = []

    for s in eligible_suppliers:
        s_curr = s.get("currency") or "INR"
        rate = 1.0
        if s_curr != base_currency and currency_rates:
            pair = f"{s_curr}_TO_{base_currency}"
            rate = currency_rates.get(pair, currency_rates.get(s_curr, 1.0))

        p = float(s["unit_price"]) * rate
        t = float(s.get("transport_cost") or 0.0) * rate
        c = int(s["capacity"])
        m = int(s.get("moq") or 1)

        cost_type = s.get("transport_cost_type", "")
        per_unit = cost_type == "per_unit" or bool(s.get("transport_is_per_unit", False))

        normalized_prices.append(p)
        normalized_transports.append(t)
        is_per_unit_transport_flags.append(per_unit)
        capacities.append(c)
        moqs.append(m)

    total_available_capacity = sum(capacities)
    if total_available_capacity < demand:
        shortfall = demand - total_available_capacity
        explanations.append(
            f"Total available capacity across all eligible suppliers ({total_available_capacity}) "
            f"is insufficient to meet requested demand ({demand}). Shortfall: {shortfall} units."
        )

        supplier_breakdown = []
        for s in supplier_dicts:
            sid = s.get("supplier_id", "UNKNOWN")
            is_el = sid not in exclusion_reasons
            supplier_breakdown.append({
                "supplier_id": sid,
                "supplier_name": s.get("supplier_name", "Unknown"),
                "allocated_quantity": 0,
                "unit_price": s.get("unit_price"),
                "transport_cost": s.get("transport_cost"),
                "landed_cost": None,
                "status": "excluded" if not is_el else "unassigned",
                "exclusion_reason": exclusion_reasons.get(sid, "Insufficient aggregate capacity"),
            })

        return {
            "status": "infeasible",
            "is_feasible": False,
            "requested_demand": demand,
            "allocated_demand": 0,
            "unmet_demand": demand,
            "total_cost": None,
            "currency": base_currency,
            "budget": budget,
            "budget_utilized_pct": None,
            "explanations": explanations,
            "allocations": [],
            "supplier_breakdown": supplier_breakdown,
            "unassigned_suppliers": [s.get("supplier_id", "UNKNOWN") for s in supplier_dicts],
            "exclusion_reasons": exclusion_reasons,
            "warnings": warnings,
        }

    # Mixed-Integer Linear Program (MILP) Formulation
    # Decision vector x of size 2*N:
    # x[0...N-1] = q_i (integer quantities allocated)
    # x[N...2*N-1] = y_i (binary selection indicators)
    c_vec = np.zeros(2 * N)
    for i in range(N):
        if is_per_unit_transport_flags[i]:
            # Transport cost scales per unit
            c_vec[i] = normalized_prices[i] + normalized_transports[i]
            c_vec[N + i] = 0.0
        else:
            # Fixed transport cost upon supplier activation
            c_vec[i] = normalized_prices[i]
            c_vec[N + i] = normalized_transports[i]

    # Integrality: all variables are integer
    integrality = np.ones(2 * N)

    # Variable Bounds
    lb = np.zeros(2 * N)
    ub = np.zeros(2 * N)
    for i in range(N):
        lb[i] = 0
        ub[i] = capacities[i]
        lb[N + i] = 0
        ub[N + i] = 1

    bounds = Bounds(lb, ub)

    # Linear Constraints
    # 1. Demand satisfaction: sum(q_i) == demand
    demand_row = np.zeros(2 * N)
    demand_row[:N] = 1.0
    demand_lb = float(demand)
    demand_ub = float(demand) if not allow_overdelivery else float(total_available_capacity)

    rows = [demand_row]
    lower_bounds = [demand_lb]
    upper_bounds = [demand_ub]

    # 2. Capacity upper bound: q_i <= capacity_i * y_i => q_i - capacity_i * y_i <= 0
    for i in range(N):
        row = np.zeros(2 * N)
        row[i] = 1.0
        row[N + i] = -float(capacities[i])
        rows.append(row)
        lower_bounds.append(-np.inf)
        upper_bounds.append(0.0)

    # 3. Minimum Order Quantity (MOQ): q_i >= moq_i * y_i => q_i - moq_i * y_i >= 0
    for i in range(N):
        row = np.zeros(2 * N)
        row[i] = 1.0
        row[N + i] = -float(moqs[i])
        rows.append(row)
        lower_bounds.append(0.0)
        upper_bounds.append(np.inf)

    # 4. Budget constraint (optional)
    if budget is not None:
        budget_row = np.copy(c_vec)
        rows.append(budget_row)
        lower_bounds.append(-np.inf)
        upper_bounds.append(float(budget))

    A_mat = np.array(rows)
    constraints = LinearConstraint(A_mat, lower_bounds, upper_bounds)

    # Solve MILP
    res = milp(c=c_vec, integrality=integrality, bounds=bounds, constraints=constraints)

    if not res.success:
        # Diagnostic analysis for infeasibility
        if budget is not None:
            # Check if feasible without budget limit
            no_budget_rows = rows[:-1]
            no_budget_lb = lower_bounds[:-1]
            no_budget_ub = upper_bounds[:-1]
            res_nobudget = milp(
                c=c_vec,
                integrality=integrality,
                bounds=bounds,
                constraints=LinearConstraint(np.array(no_budget_rows), no_budget_lb, no_budget_ub),
            )
            if res_nobudget.success:
                min_cost = round(float(res_nobudget.fun), 2)
                shortfall = round(min_cost - budget, 2)
                explanations.append(
                    f"Budget limit of {budget:,.2f} {base_currency} is insufficient. "
                    f"Minimum procurement cost to meet demand ({demand}) is {min_cost:,.2f} {base_currency} "
                    f"(budget shortfall: {shortfall:,.2f} {base_currency})."
                )
            else:
                explanations.append(
                    f"Infeasible allocation due to MOQ/capacity discrete bounds: "
                    f"no combination of eligible suppliers can fulfill exact demand of {demand} units."
                )
        else:
            min_moq = min(moqs)
            if demand < min_moq:
                explanations.append(
                    f"Demand ({demand}) is smaller than lowest supplier MOQ ({min_moq}). "
                    f"Set allow_overdelivery=True or increase order volume."
                )
            else:
                explanations.append(
                    f"Infeasible allocation: supplier MOQ and capacity bounds cannot fulfill exact demand of {demand}."
                )

        supplier_breakdown = []
        for s in supplier_dicts:
            sid = s.get("supplier_id", "UNKNOWN")
            supplier_breakdown.append({
                "supplier_id": sid,
                "supplier_name": s.get("supplier_name", "Unknown"),
                "allocated_quantity": 0,
                "unit_price": s.get("unit_price"),
                "transport_cost": s.get("transport_cost"),
                "landed_cost": None,
                "status": "excluded" if sid in exclusion_reasons else "unassigned",
                "exclusion_reason": exclusion_reasons.get(sid, "Infeasible under given constraints"),
            })

        return {
            "status": "infeasible",
            "is_feasible": False,
            "requested_demand": demand,
            "allocated_demand": 0,
            "unmet_demand": demand,
            "total_cost": None,
            "currency": base_currency,
            "budget": budget,
            "budget_utilized_pct": None,
            "explanations": explanations,
            "allocations": [],
            "supplier_breakdown": supplier_breakdown,
            "unassigned_suppliers": [s.get("supplier_id", "UNKNOWN") for s in supplier_dicts],
            "exclusion_reasons": exclusion_reasons,
            "warnings": warnings,
        }

    # Extract optimal solution
    allocated_x = res.x
    allocations_list: List[Dict[str, Any]] = []
    supplier_breakdown: List[Dict[str, Any]] = []
    unassigned_list: List[str] = []
    total_allocated = 0

    allocated_map = {}
    for i, s in enumerate(eligible_suppliers):
        q_val = int(round(allocated_x[i]))
        sup_id = s.get("supplier_id", "UNKNOWN")
        sup_name = s.get("supplier_name", "Unknown Supplier")
        cap = capacities[i]
        moq = moqs[i]

        if q_val > 0:
            total_allocated += q_val
            cost_details = calculate_landed_cost(
                supplier=s,
                quantity=q_val,
                transport_is_per_unit=is_per_unit_transport_flags[i],
                target_currency=base_currency,
                currency_rates=currency_rates,
            )
            landed = cost_details.get("total_landed_cost") or 0.0
            eff_price = round(cost_details.get("unit_price") or 0.0, 2)
            t_cost = round(cost_details.get("transport_cost") or 0.0, 2)
            unit_t_cost = round(t_cost / max(1, q_val), 2)
            utilization_pct = round((q_val / max(1, cap)) * 100.0, 2)
            share_pct = round((q_val / demand) * 100.0, 2) if demand > 0 else 0.0

            alloc_entry = {
                "supplier_id": sup_id,
                "supplier_name": sup_name,
                "allocated_quantity": q_val,
                "unit_price": eff_price,
                "effective_unit_price": eff_price,
                "transport_cost": t_cost,
                "unit_transport_cost": unit_t_cost,
                "landed_cost": landed,
                "cost_per_unit": round(landed / q_val, 4),
                "capacity": cap,
                "moq": moq,
                "capacity_utilization_pct": utilization_pct,
                "share_of_demand_pct": share_pct,
                "cost_breakdown": cost_details,
            }
            allocations_list.append(alloc_entry)
            allocated_map[sup_id] = alloc_entry

    # Build comprehensive supplier breakdown across all suppliers
    for s in supplier_dicts:
        sid = s.get("supplier_id", "UNKNOWN")
        sname = s.get("supplier_name", "Unknown")
        if sid in allocated_map:
            alloc_data = allocated_map[sid]
            supplier_breakdown.append({
                "supplier_id": sid,
                "supplier_name": sname,
                "allocated_quantity": alloc_data["allocated_quantity"],
                "unit_price": alloc_data["unit_price"],
                "transport_cost": alloc_data["transport_cost"],
                "landed_cost": alloc_data["landed_cost"],
                "capacity": alloc_data["capacity"],
                "moq": alloc_data["moq"],
                "status": "allocated",
                "exclusion_reason": None,
                "constraint_notes": f"Allocated {alloc_data['allocated_quantity']}/{alloc_data['capacity']} units ({alloc_data['capacity_utilization_pct']}% capacity)",
            })
        elif sid in exclusion_reasons:
            supplier_breakdown.append({
                "supplier_id": sid,
                "supplier_name": sname,
                "allocated_quantity": 0,
                "unit_price": s.get("unit_price"),
                "transport_cost": s.get("transport_cost"),
                "landed_cost": None,
                "capacity": s.get("capacity"),
                "moq": s.get("moq"),
                "status": "excluded",
                "exclusion_reason": exclusion_reasons[sid],
                "constraint_notes": f"Excluded from solver: {exclusion_reasons[sid]}",
            })
            unassigned_list.append(sid)
        else:
            supplier_breakdown.append({
                "supplier_id": sid,
                "supplier_name": sname,
                "allocated_quantity": 0,
                "unit_price": s.get("unit_price"),
                "transport_cost": s.get("transport_cost"),
                "landed_cost": 0.0,
                "capacity": s.get("capacity"),
                "moq": s.get("moq"),
                "status": "unassigned",
                "exclusion_reason": "Not selected: higher landed cost compared to selected suppliers",
                "constraint_notes": "Eligible but unassigned for optimal cost minimization",
            })
            unassigned_list.append(sid)

    total_cost_final = round(float(res.fun), 2)
    budget_pct = round((total_cost_final / budget) * 100.0, 2) if budget and budget > 0 else None

    explanations.append(
        f"Optimal allocation found meeting {total_allocated}/{demand} units across {len(allocations_list)} supplier(s) "
        f"for a total cost of {total_cost_final:,.2f} {base_currency}."
    )

    return {
        "status": "optimal",
        "is_feasible": True,
        "requested_demand": demand,
        "allocated_demand": total_allocated,
        "unmet_demand": max(0, demand - total_allocated),
        "total_cost": total_cost_final,
        "currency": base_currency,
        "budget": budget,
        "budget_utilized_pct": budget_pct,
        "explanations": explanations,
        "allocations": allocations_list,
        "supplier_breakdown": supplier_breakdown,
        "unassigned_suppliers": unassigned_list,
        "exclusion_reasons": exclusion_reasons,
        "warnings": warnings,
    }
