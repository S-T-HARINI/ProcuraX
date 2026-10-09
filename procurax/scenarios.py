"""
Task 3: Scenario Simulation Engine for ProcuraX.

Simulates what-if procurement scenarios:
1. Supplier price increases (single supplier or market-wide)
2. Supplier capacity reductions / disruptions
3. Combined disruption scenarios

Recalculates allocations, measures cost and quantity deltas, assesses feasibility shifts,
and generates narrative explanations of the sourcing impact.
"""

import copy
from typing import Any, Dict, List, Optional, Union
from procurax.optimizer import optimize_allocation
from procurax.models import Supplier


def simulate_scenario(
    suppliers: List[Union[Dict[str, Any], Supplier]],
    demand: int,
    scenario: Dict[str, Any],
    budget: Optional[float] = None,
    currency_rates: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Simulate a procurement risk scenario against baseline allocation.

    Args:
        suppliers: Baseline supplier list.
        demand: Total required purchase demand.
        scenario: Dict defining the disruption:
            - type: "price_increase" | "capacity_reduction" | "compound"
            - supplier_id: Target supplier ID, or "ALL" / None for global
            - percentage: Disruptive percentage change (e.g. 20.0 for 20% price hike)
            - reduction_amount: Direct unit reduction for capacity (optional alternative)
            - scenarios: List of sub-scenarios if type == "compound"
        budget: Spending limit (optional).
        currency_rates: Multi-currency conversion rates (optional).

    Returns:
        Dict conforming to ScenarioImpact schema.
    """
    # 1. Baseline optimization
    baseline_result = optimize_allocation(
        suppliers=suppliers,
        demand=demand,
        budget=budget,
        currency_rates=currency_rates,
    )

    # 2. Deep-copy suppliers for scenario modifications
    modified_suppliers: List[Dict[str, Any]] = []
    for s in suppliers:
        if isinstance(s, Supplier):
            modified_suppliers.append(s.model_dump())
        else:
            modified_suppliers.append(copy.deepcopy(dict(s)))

    # 3. Apply scenario modifications
    scenario_type = scenario.get("type", "unknown")
    applied_changes: List[str] = []

    def apply_single_scenario(sc: Dict[str, Any]):
        stype = sc.get("type")
        target_id = sc.get("supplier_id")
        pct = float(sc.get("percentage") or 0.0)
        red_amount = sc.get("reduction_amount")

        if stype == "price_increase":
            for s in modified_suppliers:
                if target_id in (None, "ALL") or s.get("supplier_id") == target_id:
                    curr_price = s.get("unit_price")
                    if curr_price is not None:
                        new_price = round(float(curr_price) * (1.0 + (pct / 100.0)), 4)
                        s["unit_price"] = new_price
                        applied_changes.append(
                            f"Increased unit price for {s.get('supplier_id')} from {curr_price} to {new_price} (+{pct}%)."
                        )

        elif stype == "capacity_reduction":
            for s in modified_suppliers:
                if target_id in (None, "ALL") or s.get("supplier_id") == target_id:
                    curr_cap = s.get("capacity")
                    if curr_cap is not None:
                        if red_amount is not None:
                            new_cap = max(0, int(curr_cap) - int(red_amount))
                            s["capacity"] = new_cap
                            applied_changes.append(
                                f"Reduced capacity for {s.get('supplier_id')} by {red_amount} units (from {curr_cap} to {new_cap})."
                            )
                        else:
                            new_cap = max(0, int(round(float(curr_cap) * (1.0 - (pct / 100.0)))))
                            s["capacity"] = new_cap
                            applied_changes.append(
                                f"Reduced capacity for {s.get('supplier_id')} by {pct}% (from {curr_cap} to {new_cap})."
                            )

    if scenario_type == "compound":
        for sub_sc in scenario.get("scenarios", []):
            apply_single_scenario(sub_sc)
    else:
        apply_single_scenario(scenario)

    # 4. Scenario optimization
    scenario_result = optimize_allocation(
        suppliers=modified_suppliers,
        demand=demand,
        budget=budget,
        currency_rates=currency_rates,
    )

    # 5. Calculate Deltas
    baseline_alloc_map = {
        a["supplier_id"]: a["allocated_quantity"] for a in baseline_result.get("allocations", [])
    }
    scenario_alloc_map = {
        a["supplier_id"]: a["allocated_quantity"] for a in scenario_result.get("allocations", [])
    }

    all_supplier_ids = set(baseline_alloc_map.keys()).union(scenario_alloc_map.keys())
    quantity_changes: Dict[str, int] = {}
    for sid in all_supplier_ids:
        old_q = baseline_alloc_map.get(sid, 0)
        new_q = scenario_alloc_map.get(sid, 0)
        if new_q != old_q:
            quantity_changes[sid] = new_q - old_q

    base_cost = baseline_result.get("total_cost")
    scen_cost = scenario_result.get("total_cost")

    total_cost_delta: Optional[float] = None
    percentage_cost_change: Optional[float] = None

    if base_cost is not None and scen_cost is not None:
        total_cost_delta = round(scen_cost - base_cost, 2)
        if base_cost > 0:
            percentage_cost_change = round((total_cost_delta / base_cost) * 100.0, 2)

    # 6. Generate narrative explanation
    narrative_parts: List[str] = []
    narrative_parts.append(f"Scenario Applied: {'; '.join(applied_changes) if applied_changes else scenario_type}.")

    if baseline_result.get("is_feasible") and not scenario_result.get("is_feasible"):
        narrative_parts.append(
            f"FEASIBILITY LOSS: Sourcing became INFEASIBLE under this scenario. "
            f"Reason: {' '.join(scenario_result.get('explanations', []))}"
        )
    elif not baseline_result.get("is_feasible") and scenario_result.get("is_feasible"):
        narrative_parts.append("FEASIBILITY RESTORED: Allocation is now feasible.")
    elif baseline_result.get("is_feasible") and scenario_result.get("is_feasible"):
        if total_cost_delta is not None:
            if total_cost_delta > 0:
                narrative_parts.append(
                    f"Cost increased by {total_cost_delta:,.2f} ({percentage_cost_change}% change), "
                    f"raising total procurement spend to {scen_cost:,.2f}."
                )
            elif total_cost_delta < 0:
                narrative_parts.append(
                    f"Cost decreased by {abs(total_cost_delta):,.2f} ({percentage_cost_change}% change), "
                    f"lowering total procurement spend to {scen_cost:,.2f}."
                )
            else:
                narrative_parts.append("Total procurement cost remained unchanged.")

        # Reallocation movements
        shifts = []
        for sid, delta in quantity_changes.items():
            if delta > 0:
                shifts.append(f"{sid} (+{delta} units)")
            elif delta < 0:
                shifts.append(f"{sid} ({delta} units)")
        if shifts:
            narrative_parts.append(f"Volume reallocation: {', '.join(shifts)}.")
        else:
            narrative_parts.append("Supplier order volumes remained identical.")
    else:
        narrative_parts.append(
            f"Allocation remains infeasible. "
            f"Reason: {' '.join(scenario_result.get('explanations', []))}"
        )

    return {
        "scenario_type": scenario_type,
        "parameters": scenario,
        "baseline_status": baseline_result.get("status", "unknown"),
        "scenario_status": scenario_result.get("status", "unknown"),
        "is_feasible": scenario_result.get("is_feasible", False),
        "total_cost_delta": total_cost_delta,
        "percentage_cost_change": percentage_cost_change,
        "quantity_changes": quantity_changes,
        "narrative_explanation": " ".join(narrative_parts),
        "baseline_summary": baseline_result,
        "scenario_summary": scenario_result,
    }
