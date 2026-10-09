"""
Unit tests for Task 9: Service Integration Adapters (Person 2 Interface Compatibility)
"""

import pytest
from procurax.services import (
    ProcuraXOptimizationService,
    ProcuraXGraphService,
    OptimizationRequest,
    OptimizationScenario,
    GraphRequest,
)


@pytest.fixture
def service_test_suppliers():
    return [
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
            "sustainability_claims": ["100% Recycled PET"],
            "missing_fields": [],
            "claims": [
                {
                    "field": "unit_price",
                    "value": 80.0,
                    "source_file": "quote1.pdf",
                    "source_page": 1,
                    "source_excerpt": "Unit Price: 80 INR",
                    "status": "extracted",
                }
            ],
        },
        {
            "supplier_id": "SUP-002",
            "supplier_name": "PrimeHoldings Corp",
            "product_name": "Reusable Bottle",
            "unit_price": 70.0,
            "currency": "INR",
            "moq": 50,
            "capacity": 300,
            "delivery_days": 7,
            "transport_cost": 600.0,
            "sustainability_claims": [],
            "missing_fields": [],
            "claims": [
                {
                    "field": "unit_price",
                    "value": 70.0,
                    "source_file": "quote2.xlsx",
                    "source_page": 1,
                    "source_excerpt": "Unit Price: 70 INR",
                    "status": "extracted",
                }
            ],
        },
    ]


def test_procurax_optimization_service(service_test_suppliers):
    optimizer = ProcuraXOptimizationService()

    # Request for 400 units, budget 35000
    req = OptimizationRequest(
        suppliers=service_test_suppliers,
        target_demand=400,
        budget_limit=35000.0,
    )

    response = optimizer.optimize(req)

    assert response.status == "optimal"
    assert response.target_demand == 400
    assert response.total_allocated_quantity == 400
    assert response.unmet_demand == 0
    assert response.is_mock is False
    assert len(response.allocations) >= 1

    # Verify SupplierAllocation attributes expected by Person 2
    for alloc in response.allocations:
        assert alloc.supplier_id in ("SUP-001", "SUP-002")
        assert alloc.allocated_quantity > 0
        assert alloc.effective_unit_price > 0
        assert alloc.landed_cost > 0
        assert alloc.capacity_utilization_pct > 0


def test_procurax_optimization_service_with_scenario(service_test_suppliers):
    optimizer = ProcuraXOptimizationService()

    # Scenario: SUP-002 price surged by 30% (multiplier 1.30: 70 * 1.30 = 91)
    scenario = OptimizationScenario(
        price_multipliers={"SUP-002": 1.30},
    )
    req = OptimizationRequest(
        suppliers=service_test_suppliers,
        target_demand=300,
        scenario=scenario,
    )

    response = optimizer.optimize(req)
    assert response.status == "optimal"
    assert response.total_allocated_quantity == 300
    # Cheaper supplier is now SUP-001 (80 vs 91)
    alloc_map = {a.supplier_id: a.allocated_quantity for a in response.allocations}
    assert alloc_map.get("SUP-001") == 300


def test_procurax_graph_service(service_test_suppliers):
    optimizer = ProcuraXOptimizationService()
    graph_service = ProcuraXGraphService()

    opt_req = OptimizationRequest(suppliers=service_test_suppliers, target_demand=200)
    opt_res = optimizer.optimize(opt_req)

    graph_req = GraphRequest(suppliers=service_test_suppliers, optimization_result=opt_res)
    graph_res = graph_service.build_graph(graph_req)

    assert graph_res.is_mock is False
    assert len(graph_res.nodes) > 0
    assert len(graph_res.edges) > 0

    node_types = {n.type for n in graph_res.nodes}
    assert len(node_types) > 1
