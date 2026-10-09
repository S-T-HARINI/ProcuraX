"""
End-to-end reproducible demonstration of ProcuraX Procurement Intelligence Engine (Person 3).
Demonstrates:
1. Deterministic landed cost calculation with documented transport assumptions.
2. MILP supplier allocation respecting demand, capacity, MOQ, and budget constraints.
3. What-if scenario simulation with baseline-vs-scenario delta analysis.
4. NetworkX Evidence-to-Decision Consistency Graph generation and decision audit.

All demonstration data is explicitly SYNTHETIC.
"""

import json
from pathlib import Path
from procurax import (
    calculate_landed_cost,
    optimize_allocation,
    simulate_scenario,
    build_evidence_graph,
)

# Load clearly labeled synthetic dataset
DATASET_PATH = Path(__file__).parent / "data" / "synthetic_demo_suppliers.json"


def load_demo_dataset():
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def run_demonstration():
    print("=" * 75)
    print("ProcuraX: Evidence-Driven Procurement Intelligence & Optimization Demo")
    print("NOTE: All supplier data in this demonstration is strictly SYNTHETIC.")
    print("=" * 75)

    suppliers = load_demo_dataset()
    print(f"Loaded {len(suppliers)} synthetic supplier quotations from {DATASET_PATH.name}.\n")

    # 1. Landed Cost Calculation (Task 1)
    print("-" * 75)
    print("STEP 1: Landed-Cost Calculation (Transport Cost Assumption: Fixed Per Shipment)")
    print("-" * 75)
    sup_1 = suppliers[0]
    cost_res_flat = calculate_landed_cost(sup_1, quantity=250, transport_is_per_unit=False)
    print(f"Supplier: {cost_res_flat['supplier_name']} ({cost_res_flat['supplier_id']})")
    print(f"  Order Quantity:          {cost_res_flat['quantity']} units")
    print(f"  Quoted Unit Price:       {cost_res_flat['unit_price']} {cost_res_flat['currency']}")
    print(f"  Transport Cost Mode:     {cost_res_flat['transport_cost_mode']} (Flat per order)")
    print(f"  Transport Cost Charge:   {cost_res_flat['transport_cost']} {cost_res_flat['currency']}")
    print(f"  Total Landed Cost:       {cost_res_flat['total_landed_cost']:,.2f} {cost_res_flat['currency']}")
    print(f"  Effective Cost / Unit:   {cost_res_flat['cost_per_unit']} {cost_res_flat['currency']}")
    print(f"  Data Inputs Complete:    {cost_res_flat['is_complete']}\n")

    # Also test incomplete supplier (SUP-004) to demonstrate zero assumption prevention
    sup_4 = suppliers[3]
    cost_res_inc = calculate_landed_cost(sup_4, quantity=100)
    print(f"Incomplete Supplier Check ({sup_4['supplier_id']}):")
    print(f"  Total Landed Cost:       {cost_res_inc['total_landed_cost']} (Never assumed 0!)")
    print(f"  Missing Inputs Flagged:  {cost_res_inc['missing_cost_inputs']}")
    print(f"  Inputs Complete Flag:    {cost_res_inc['is_complete']}\n")

    # 2. Supplier Allocation Optimization (Task 2 & 3)
    target_demand = 600
    budget_limit = 52000.0
    print("-" * 75)
    print(f"STEP 2: MILP Supplier Allocation (Demand: {target_demand} units, Budget: {budget_limit:,.2f} INR)")
    print("-" * 75)
    alloc_res = optimize_allocation(suppliers, demand=target_demand, budget=budget_limit)
    print(f"Solver Status:             {alloc_res['status']} (Feasible: {alloc_res['is_feasible']})")
    print(f"Target Demand:             {alloc_res['requested_demand']} units")
    print(f"Allocated Demand:          {alloc_res['allocated_demand']} units (Unmet: {alloc_res['unmet_demand']})")
    print(f"Total Procurement Spend:   {alloc_res['total_cost']:,.2f} {alloc_res['currency']}")
    print(f"Budget Utilization:        {alloc_res['budget_utilized_pct']}%\n")

    print("Supplier Breakdown & Allocation Decisions:")
    for b in alloc_res["supplier_breakdown"]:
        status_tag = f"[{b['status'].upper()}]".ljust(12)
        if b['status'] == 'allocated':
            print(f"  {status_tag} {b['supplier_name']} ({b['supplier_id']}): "
                  f"{b['allocated_quantity']} units | Landed: {b['landed_cost']:,.2f} INR | Notes: {b['constraint_notes']}")
        else:
            print(f"  {status_tag} {b['supplier_name']} ({b['supplier_id']}): "
                  f"0 units | Reason: {b['exclusion_reason']}")

    print(f"\nExplanation: {alloc_res['explanations'][0]}\n")

    # 3. What-If Scenario Simulation (Task 4)
    print("-" * 75)
    print("STEP 3: Scenario Simulation: 25% Price Surge at Primary Supplier (SUP-002)")
    print("-" * 75)
    price_shock_scenario = {
        "type": "price_increase",
        "supplier_id": "SUP-002",
        "percentage": 25.0,
    }
    scen_res = simulate_scenario(suppliers, demand=target_demand, scenario=price_shock_scenario, budget=budget_limit)
    print(f"Scenario Impact Narrative: {scen_res['narrative_explanation']}")
    print(f"Procurement Spend Delta:   {scen_res['total_cost_delta']:+,.2f} INR ({scen_res['percentage_cost_change']:+}% change)")
    print("Volume Reallocations:")
    for sid, delta in scen_res["quantity_changes"].items():
        print(f"  - {sid}: {delta:+d} units")
    print()

    # 4. Evidence-to-Decision Consistency Graph (Task 5, 6, 7)
    print("-" * 75)
    print("STEP 4: Evidence-to-Decision Consistency Graph (NetworkX)")
    print("-" * 75)
    graph_res = build_evidence_graph(
        suppliers=suppliers,
        allocation_result=alloc_res,
        scenario_impact=scen_res,
        risks=[
            {
                "supplier_id": "SUP-002",
                "risk_type": "Capacity Utilization Bottleneck",
                "severity": "medium",
                "description": "Utilizing 100% of maximum factory batch output.",
            }
        ],
    )
    metrics = graph_res["graph_metrics"]
    audit = graph_res["decision_audit"]

    print(f"Graph Node Count:          {metrics['node_count']}")
    print(f"Graph Edge Count:          {metrics['edge_count']}")
    print(f"Node Types Modeled:        {metrics['node_types']}")
    print(f"Edge Types Modeled:        {metrics['edge_types']}")
    print(f"Referenced Source Files:   {audit['documents_referenced']}")
    print(f"Unverified Claims Flagged: {audit['unverified_claims_count']} (never assumed as ground-truth facts)")
    print(f"Recommendation Caution:    relies_on_incomplete_data = {audit['depends_on_incomplete_data']}")
    print(f"Affected Suppliers:        {audit['affected_suppliers']} (SUP-003 has unverified/missing delivery_days)")

    print("\n" + "=" * 75)
    print("ProcuraX Person 3 pipeline completed deterministically on CPU!")
    print("=" * 75)


if __name__ == "__main__":
    run_demonstration()
