"""
Task 2: Supplier Allocation Optimizer for ProcuraX.

Solves the procurement supplier allocation problem using Mixed-Integer Linear Programming (MILP).
Constraints handled:
1. Demand satisfaction: sum(q_i) == demand
2. Minimum Order Quantity (MOQ): either q_i == 0 or q_i >= moq_i
3. Supplier Capacity: q_i <= capacity_i
4. Budget: total_cost <= budget (when provided)
5. Non-negativity and integer quantities

Provides clear diagnostic explanations for infeasibility (insufficient capacity,
MOQ conflicts, budget limits, missing supplier data).
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

    Returns:
        Dict conforming to OptimizationSummary schema.
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

    # Currency validation
    currencies_found = set()
    for s in supplier_dicts:
        curr = s.get("currency")
        if curr:
            currencies_found.add(curr)
        else:
            currencies_found.add("INR")

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
            "unassigned_suppliers": [s.get("supplier_id", "UNKNOWN") for s in supplier_dicts],
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
            "unassigned_suppliers": [s.get("supplier_id", "UNKNOWN") for s in supplier_dicts],
            "warnings": warnings,
        }

    # Filter eligible suppliers (must have unit_price and capacity)
    eligible_suppliers: List[Dict[str, Any]] = []
    ineligible_suppliers: List[str] = []

    for s in supplier_dicts:
        sup_id = s.get("supplier_id", "UNKNOWN")
        unit_price = s.get("unit_price")
        capacity = s.get("capacity")

        missing_reasons = []
        if unit_price is None:
            missing_reasons.append("unit_price is missing/null")
        if capacity is None:
            missing_reasons.append("capacity is missing/null")
        elif capacity <= 0:
            missing_reasons.append(f"capacity is non-positive ({capacity})")

        if missing_reasons:
            ineligible_suppliers.append(sup_id)
            warnings.append(f"Excluded supplier {sup_id} from allocation: {', '.join(missing_reasons)}.")
        else:
            eligible_suppliers.append(s)

    if not eligible_suppliers:
        explanations.append("No eligible suppliers available with valid unit_price and capacity.")
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
            "unassigned_suppliers": [s.get("supplier_id", "UNKNOWN") for s in supplier_dicts],
            "warnings": warnings,
        }

    N = len(eligible_suppliers)

    # Convert supplier costs to base currency
    normalized_prices = []
    normalized_transports = []
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

        normalized_prices.append(p)
        normalized_transports.append(t)
        capacities.append(c)
        moqs.append(m)

    total_available_capacity = sum(capacities)
    if total_available_capacity < demand:
        explanations.append(
            f"Total available capacity across all eligible suppliers ({total_available_capacity}) "
            f"is insufficient to meet requested demand ({demand}). Shortfall: {demand - total_available_capacity} units."
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
            "explanations": explanations,
            "allocations": [],
            "unassigned_suppliers": [s.get("supplier_id", "UNKNOWN") for s in supplier_dicts],
            "warnings": warnings,
        }

    # Formulation of Mixed-Integer Linear Program (MILP)
    # Decision vector x of size 2*N:
    # x[0...N-1] = q_i (integer quantities)
    # x[N...2*N-1] = y_i (binary selection indicators 0 or 1)
    c_vec = np.zeros(2 * N)
    for i in range(N):
        c_vec[i] = normalized_prices[i]       # cost per unit
        c_vec[N + i] = normalized_transports[i] # fixed transport cost upon activation

    # Integrality: all variables are integer (1: integer, 0: continuous)
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

    # Constraints list
    # Row 1: Demand satisfaction: sum(q_i) == demand (or >= demand if overdelivery allowed)
    demand_row = np.zeros(2 * N)
    demand_row[:N] = 1.0
    demand_lb = float(demand)
    demand_ub = float(demand) if not allow_overdelivery else float(total_available_capacity)

    rows = [demand_row]
    lower_bounds = [demand_lb]
    upper_bounds = [demand_ub]

    # Linking constraints:
    # 1. Capacity: q_i <= capacity_i * y_i  =>  q_i - capacity_i * y_i <= 0
    for i in range(N):
        row = np.zeros(2 * N)
        row[i] = 1.0
        row[N + i] = -float(capacities[i])
        rows.append(row)
        lower_bounds.append(-np.inf)
        upper_bounds.append(0.0)

    # 2. Minimum Order Quantity (MOQ): q_i >= moq_i * y_i  =>  q_i - moq_i * y_i >= 0
    for i in range(N):
        row = np.zeros(2 * N)
        row[i] = 1.0
        row[N + i] = -float(moqs[i])
        rows.append(row)
        lower_bounds.append(0.0)
        upper_bounds.append(np.inf)

    # 3. Budget constraint (optional)
    if budget is not None:
        budget_row = np.zeros(2 * N)
        for i in range(N):
            budget_row[i] = normalized_prices[i]
            budget_row[N + i] = normalized_transports[i]
        rows.append(budget_row)
        lower_bounds.append(-np.inf)
        upper_bounds.append(float(budget))

    A_mat = np.array(rows)
    constraints = LinearConstraint(A_mat, lower_bounds, upper_bounds)

    # Solve MILP
    res = milp(c=c_vec, integrality=integrality, bounds=bounds, constraints=constraints)

    if not res.success:
        # Investigate cause of infeasibility
        # Check if budget was the restrictive factor by solving without budget constraint
        if budget is not None:
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
                explanations.append(
                    f"Budget limit of {budget:,.2f} {base_currency} is insufficient. "
                    f"Minimum procurement cost to meet demand ({demand}) is {min_cost:,.2f} {base_currency} "
                    f"(shortfall: {min_cost - budget:,.2f} {base_currency})."
                )
            else:
                explanations.append(
                    f"Infeasible allocation due to MOQ or capacity granularity constraints: "
                    f"unable to satisfy exact demand of {demand} units with available supplier MOQ requirements."
                )
        else:
            # Check MOQ vs demand conflict
            min_moq = min(moqs)
            if demand < min_moq:
                explanations.append(
                    f"Demand ({demand}) is smaller than lowest supplier MOQ ({min_moq}). "
                    f"Set allow_overdelivery=True or adjust demand."
                )
            else:
                explanations.append(
                    f"Infeasible allocation: supplier MOQ and capacity bounds cannot be satisfied for exact demand of {demand}."
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
            "explanations": explanations,
            "allocations": [],
            "unassigned_suppliers": [s.get("supplier_id", "UNKNOWN") for s in supplier_dicts],
            "warnings": warnings,
        }

    # Extract optimal solution
    allocated_x = res.x
    allocations_list: List[Dict[str, Any]] = []
    unassigned_list: List[str] = list(ineligible_suppliers)
    total_allocated = 0
    total_cost_calc = 0.0

    for i, s in enumerate(eligible_suppliers):
        q_val = int(round(allocated_x[i]))
        sup_id = s.get("supplier_id", "UNKNOWN")
        sup_name = s.get("supplier_name", "Unknown Supplier")

        if q_val > 0:
            total_allocated += q_val
            # Landed cost calculation for transparency
            cost_details = calculate_landed_cost(
                supplier=s,
                quantity=q_val,
                target_currency=base_currency,
                currency_rates=currency_rates,
            )
            total_cost_calc += cost_details.get("total_landed_cost") or 0.0

            share_pct = round((q_val / demand) * 100.0, 2) if demand > 0 else 0.0
            allocations_list.append({
                "supplier_id": sup_id,
                "supplier_name": sup_name,
                "allocated_quantity": q_val,
                "cost_breakdown": cost_details,
                "capacity": capacities[i],
                "moq": moqs[i],
                "share_of_demand_pct": share_pct,
            })
        else:
            unassigned_list.append(sup_id)

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
        "unassigned_suppliers": unassigned_list,
        "warnings": warnings,
    }
