"""
End-to-end demonstration of ProcuraX Procurement Intelligence Engine (Person 3).
Demonstrates landed cost, MILP allocation, scenario simulation, and graph generation.
"""

import json
from procurax import (
    calculate_landed_cost,
    optimize_allocation,
    simulate_scenario,
    build_procurement_graph,
)

# Synthetic Demonstration Suppliers conforming to the Universal Prompt contract
DEMO_SUPPLIERS = [
    {
        "supplier_id": "SUP-001",
        "supplier_name": "EcoPak Packaging",
        "product_name": "Reusable Bottle",
        "unit_price": 80.0,
        "currency": "INR",
        "moq": 100,
        "capacity": 600,
        "delivery_days": 5,
        "transport_cost": 500.0,
        "sustainability_claims": ["100% PCR recycled material"],
        "missing_fields": [],
        "claims": [
            {
                "field": "unit_price",
                "value": 80.0,
                "source_file": "quotation_ecopak.pdf",
                "source_page": 1,
                "source_excerpt": "Quoted unit price INR 80.00 for orders exceeding 100 units.",
                "status": "extracted",
            },
            {
                "field": "capacity",
                "value": 600,
                "source_file": "quotation_ecopak.pdf",
                "source_page": 2,
                "source_excerpt": "Monthly plant allocation capacity: 600 units.",
                "status": "extracted",
            },
        ],
    },
    {
        "supplier_id": "SUP-002",
        "supplier_name": "PrimeHoldings Corp",
        "product_name": "Reusable Bottle",
        "unit_price": 72.0,
        "currency": "INR",
        "moq": 150,
        "capacity": 300,
        "delivery_days": 7,
        "transport_cost": 800.0,
        "sustainability_claims": [],
        "missing_fields": [],
        "claims": [
            {
                "field": "unit_price",
                "value": 72.0,
                "source_file": "prime_rate_card.xlsx",
                "source_page": 1,
                "source_excerpt": "Rate: 72 INR per bottle; Minimum shipment 150 units.",
                "status": "extracted",
            }
        ],
    },
    {
        "supplier_id": "SUP-003",
        "supplier_name": "AeroPlastic Solutions",
        "product_name": "Reusable Bottle",
        "unit_price": 76.0,
        "currency": "INR",
        "moq": 50,
        "capacity": 400,
        "delivery_days": None,  # Incomplete data!
        "transport_cost": 350.0,
        "sustainability_claims": ["ISO 14001 Certified"],
        "missing_fields": ["delivery_days"],
        "claims": [
            {
                "field": "unit_price",
                "value": 76.0,
                "source_file": "aeroplastic_quote.pdf",
                "source_page": 1,
                "source_excerpt": "Unit rate INR 76.00 ex-factory.",
                "status": "extracted",
            }
        ],
    },
]


def run_demonstration():
    print("=" * 70)
    print("ProcuraX: Procurement Optimization & Consistency Graph Demo")
    print("=" * 70)

    # 1. Landed Cost Calculation
    print("\n[1] Landed Cost Calculation for SUP-001 (Quantity: 200 units):")
    cost_res = calculate_landed_cost(DEMO_SUPPLIERS[0], quantity=200)
    print(f"    Total Landed Cost: {cost_res['total_landed_cost']} {cost_res['currency']}")
    print(f"    Effective Cost Per Unit: {cost_res['cost_per_unit']} {cost_res['currency']}")
    print(f"    Cost Inputs Complete: {cost_res['is_complete']}")

    # 2. Optimal Supplier Allocation
    demand = 500
    budget = 45000.0
    print(f"\n[2] Optimizing Sourcing Allocation for Demand = {demand} units (Budget = {budget:,.2f} INR):")
    alloc_res = optimize_allocation(DEMO_SUPPLIERS, demand=demand, budget=budget)
    print(f"    Status: {alloc_res['status']} (Feasible: {alloc_res['is_feasible']})")
    print(f"    Total Optimized Cost: {alloc_res['total_cost']:,.2f} {alloc_res['currency']}")
    print(f"    Budget Utilization: {alloc_res['budget_utilized_pct']}%")
    print("    Supplier Splits:")
    for a in alloc_res["allocations"]:
        print(f"      - {a['supplier_name']} ({a['supplier_id']}): {a['allocated_quantity']} units ({a['share_of_demand_pct']}%)")
    print(f"    Explanations: {alloc_res['explanations'][0]}")

    # 3. Scenario Simulation: Price Shock
    price_scenario = {
        "type": "price_increase",
        "supplier_id": "SUP-002",
        "percentage": 25.0,
    }
    print(f"\n[3] Simulating What-If Scenario: 25% price surge at SUP-002:")
    scen_res = simulate_scenario(DEMO_SUPPLIERS, demand=demand, scenario=price_scenario, budget=budget)
    print(f"    Impact: {scen_res['narrative_explanation']}")
    print(f"    Total Spend Delta: {scen_res['total_cost_delta']:+,.2f} INR")

    # 4. Evidence-to-Decision Consistency Graph
    print(f"\n[4] Building Evidence-to-Decision Consistency Graph:")
    graph_res = build_procurement_graph(
        suppliers=DEMO_SUPPLIERS,
        allocation=alloc_res,
        risks=[
            {
                "supplier_id": "SUP-002",
                "risk_type": "Capacity Bottleneck",
                "severity": "medium",
                "description": "Utilizing 100% of available plant capacity.",
            }
        ],
    )
    print(f"    Graph Nodes: {graph_res['graph_metrics']['node_count']}")
    print(f"    Graph Edges: {graph_res['graph_metrics']['edge_count']}")
    print(f"    Node Types: {graph_res['graph_metrics']['node_types']}")
    print(f"    Edge Types: {graph_res['graph_metrics']['edge_types']}")
    print(f"    Recommendation Relies on Incomplete Data: {graph_res['decision_audit']['depends_on_incomplete_data']}")
    print(f"    Affected Suppliers in Recommendation: {graph_res['decision_audit']['affected_suppliers']}")
    print(f"    Unverified Claims Count: {graph_res['decision_audit']['unverified_claims_count']}")

    print("\n" + "=" * 70)
    print("All Person 3 modules executed deterministically on CPU!")
    print("=" * 70)


if __name__ == "__main__":
    run_demonstration()
