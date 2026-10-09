"""
Task 3: Scenario Simulation Engine for ProcuraX.

Simulates what-if procurement risk scenarios:
1. Supplier price increases (single supplier or market-wide, percentage or multipliers)
2. Transport-cost changes (fuel surcharges, freight increases, fixed or percentage)
3. Supplier capacity reductions / bottlenecks
4. Supplier unavailability / factory shutdowns
5. Compound and multi-disruption scenarios

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
    scenario: Union[Dict[str, Any], Any],
    budget: Optional[float] = None,
    currency_rates: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Simulate a procurement risk scenario against baseline allocation.

    Args:
        suppliers: Baseline supplier list.
        demand: Total required purchase demand.
        scenario: Dict or Pydantic OptimizationScenario defining the disruption:
            - type: "price_increase" | "transport_cost_change" | "capacity_reduction" | "supplier_unavailability" | "compound"
            - supplier_id: Target supplier ID, or "ALL" / None for global
            - percentage: Percentage change (e.g., 20.0 for 20% increase/reduction)
            - amount: Absolute cost delta or unit change
            - price_multipliers: dict[str, float] (Person 2 compatibility, e.g. {"SUP-001": 1.25})
            - capacity_reductions: dict[str, float] (e.g. {"SUP-001": 0.50} for 50% cut)
            - transport_multipliers: dict[str, float] (e.g. {"SUP-001": 1.30})
            - unavailable_suppliers: list[str] (e.g. ["SUP-002"])
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
        elif hasattr(s, "model_dump"):
            modified_suppliers.append(s.model_dump())
        else:
            modified_suppliers.append(copy.deepcopy(dict(s)))

    # Convert Pydantic scenario if needed
    if hasattr(scenario, "model_dump"):
        sc_dict = scenario.model_dump()
    elif isinstance(scenario, dict):
        sc_dict = dict(scenario)
    else:
        sc_dict = {"type": "unknown"}

    scenario_type = sc_dict.get("type", "custom")
    applied_changes: List[str] = []
    unavailable_list: List[str] = []

    def apply_single_scenario(sc: Dict[str, Any]):
        stype = sc.get("type")
        target_id = sc.get("supplier_id")
        pct = float(sc.get("percentage") or 0.0)
        amt = sc.get("amount")
        red_amount = sc.get("reduction_amount")

        # 1. Price increases / multipliers
        if stype in ("price_increase", "price_change"):
            for s in modified_suppliers:
                sid = s.get("supplier_id")
                if target_id in (None, "ALL") or sid == target_id:
                    curr_price = s.get("unit_price")
                    if curr_price is not None:
                        if amt is not None:
                            new_price = round(max(0.0, float(curr_price) + float(amt)), 4)
                            s["unit_price"] = new_price
                            applied_changes.append(
                                f"Changed unit price for {sid} from {curr_price} to {new_price} ({amt:+})."
                            )
                        else:
                            new_price = round(float(curr_price) * (1.0 + (pct / 100.0)), 4)
                            s["unit_price"] = new_price
                            applied_changes.append(
                                f"Increased unit price for {sid} from {curr_price} to {new_price} (+{pct}%)."
                            )

        # 2. Transport cost changes (fuel surge, carrier changes)
        elif stype in ("transport_cost_change", "transport_change", "transport_increase"):
            for s in modified_suppliers:
                sid = s.get("supplier_id")
                if target_id in (None, "ALL") or sid == target_id:
                    curr_t = s.get("transport_cost")
                    if curr_t is not None:
                        if amt is not None:
                            new_t = round(max(0.0, float(curr_t) + float(amt)), 2)
                            s["transport_cost"] = new_t
                            applied_changes.append(
                                f"Adjusted transport cost for {sid} from {curr_t} to {new_t} ({amt:+})."
                            )
                        else:
                            new_t = round(float(curr_t) * (1.0 + (pct / 100.0)), 2)
                            s["transport_cost"] = new_t
                            applied_changes.append(
                                f"Adjusted transport cost for {sid} from {curr_t} to {new_t} (+{pct}%)."
                            )

        # 3. Capacity reductions
        elif stype in ("capacity_reduction", "capacity_drop"):
            for s in modified_suppliers:
                sid = s.get("supplier_id")
                if target_id in (None, "ALL") or sid == target_id:
                    curr_cap = s.get("capacity")
                    if curr_cap is not None:
                        if red_amount is not None:
                            new_cap = max(0, int(curr_cap) - int(red_amount))
                            s["capacity"] = new_cap
                            applied_changes.append(
                                f"Reduced capacity for {sid} by {red_amount} units (from {curr_cap} to {new_cap})."
                            )
                        else:
                            new_cap = max(0, int(round(float(curr_cap) * (1.0 - (pct / 100.0)))))
                            s["capacity"] = new_cap
                            applied_changes.append(
                                f"Reduced capacity for {sid} by {pct}% (from {curr_cap} to {new_cap})."
                            )

        # 4. Supplier unavailability / factory shutdowns
        elif stype in ("supplier_unavailability", "supplier_shutdown", "unavailability"):
            targets = [target_id] if target_id else sc.get("supplier_ids", [])
            for tid in targets:
                if tid:
                    unavailable_list.append(tid)
                    for s in modified_suppliers:
                        if s.get("supplier_id") == tid:
                            s["is_available"] = False
                            s["capacity"] = 0
                            applied_changes.append(f"Supplier {tid} marked UNAVAILABLE (capacity set to 0).")

    # Support Person 2's OptimizationScenario schema (price_multipliers & capacity_reductions)
    if "price_multipliers" in sc_dict:
        for sid, mult in sc_dict["price_multipliers"].items():
            for s in modified_suppliers:
                if s.get("supplier_id") == sid and s.get("unit_price") is not None:
                    old_p = s["unit_price"]
                    new_p = round(float(old_p) * float(mult), 4)
                    s["unit_price"] = new_p
                    applied_changes.append(f"Applied price multiplier {mult}x to {sid} ({old_p} -> {new_p}).")

    if "capacity_reductions" in sc_dict:
        for sid, ratio in sc_dict["capacity_reductions"].items():
            for s in modified_suppliers:
                if s.get("supplier_id") == sid and s.get("capacity") is not None:
                    old_c = s["capacity"]
                    new_c = max(0, int(round(float(old_c) * (1.0 - float(ratio)))))
                    s["capacity"] = new_c
                    applied_changes.append(f"Applied capacity reduction of {ratio*100}% to {sid} ({old_c} -> {new_c}).")

    if "transport_multipliers" in sc_dict:
        for sid, mult in sc_dict["transport_multipliers"].items():
            for s in modified_suppliers:
                if s.get("supplier_id") == sid and s.get("transport_cost") is not None:
                    old_t = s["transport_cost"]
                    new_t = round(float(old_t) * float(mult), 2)
                    s["transport_cost"] = new_t
                    applied_changes.append(f"Applied transport multiplier {mult}x to {sid} ({old_t} -> {new_t}).")

    if "unavailable_suppliers" in sc_dict:
        for sid in sc_dict["unavailable_suppliers"]:
            unavailable_list.append(sid)
            for s in modified_suppliers:
                if s.get("supplier_id") == sid:
                    s["is_available"] = False
                    s["capacity"] = 0
                    applied_changes.append(f"Supplier {sid} marked UNAVAILABLE.")

    if scenario_type == "compound":
        for sub_sc in sc_dict.get("scenarios", []):
            apply_single_scenario(sub_sc)
    else:
        apply_single_scenario(sc_dict)

    # 4. Scenario optimization
    scenario_result = optimize_allocation(
        suppliers=modified_suppliers,
        demand=demand,
        budget=budget,
        currency_rates=currency_rates,
        unavailable_suppliers=unavailable_list,
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
        "parameters": sc_dict,
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
