"""
Unit tests for Task 2: optimize_allocation
"""

import pytest
from procurax.optimizer import optimize_allocation


@pytest.fixture
def sample_suppliers():
    return [
        {
            "supplier_id": "SUP-001",
            "supplier_name": "Supplier A",
            "unit_price": 50.0,
            "transport_cost": 200.0,
            "moq": 50,
            "capacity": 300,
            "currency": "INR",
        },
        {
            "supplier_id": "SUP-002",
            "supplier_name": "Supplier B",
            "unit_price": 45.0,
            "transport_cost": 500.0,
            "moq": 100,
            "capacity": 200,
            "currency": "INR",
        },
        {
            "supplier_id": "SUP-003",
            "supplier_name": "Supplier C",
            "unit_price": 60.0,
            "transport_cost": 100.0,
            "moq": 10,
            "capacity": 500,
            "currency": "INR",
        },
    ]


def test_optimizer_demand_fulfillment(sample_suppliers):
    # Demand = 200: Supplier B (cheapest unit price 45) can supply up to 200 units!
    # Cost for B: 200 * 45 + 500 = 9500
    # Cost for A: 200 * 50 + 200 = 10200
    result = optimize_allocation(sample_suppliers, demand=200)
    assert result["is_feasible"] is True
    assert result["status"] == "optimal"
    assert result["allocated_demand"] == 200
    assert result["unmet_demand"] == 0
    assert len(result["allocations"]) >= 1
    # Check that supplier B was selected
    alloc_ids = [a["supplier_id"] for a in result["allocations"]]
    assert "SUP-002" in alloc_ids
    assert result["total_cost"] == 9500.0


def test_optimizer_capacity_and_split(sample_suppliers):
    # Demand = 400: Supplier B capacity is 200, Supplier A capacity is 300
    # Cheaper B takes 200, then A takes 200
    # Total cost = (200*45 + 500) + (200*50 + 200) = 9500 + 10200 = 19700
    result = optimize_allocation(sample_suppliers, demand=400)
    assert result["is_feasible"] is True
    assert result["allocated_demand"] == 400
    allocations = {a["supplier_id"]: a["allocated_quantity"] for a in result["allocations"]}
    assert allocations.get("SUP-002") == 200
    assert allocations.get("SUP-001") == 200
    assert result["total_cost"] == 19700.0


def test_optimizer_moq_enforcement(sample_suppliers):
    # Demand = 30: Supplier B has MOQ 100, Supplier A has MOQ 50, Supplier C has MOQ 10
    # Neither A nor B can be selected because their MOQ > 30.
    # Only Supplier C can fulfill 30 units!
    result = optimize_allocation(sample_suppliers, demand=30)
    assert result["is_feasible"] is True
    assert result["allocated_demand"] == 30
    assert len(result["allocations"]) == 1
    assert result["allocations"][0]["supplier_id"] == "SUP-003"
    assert result["allocations"][0]["allocated_quantity"] == 30


def test_optimizer_budget_constraint(sample_suppliers):
    # Demand = 200, minimum cost is 9500
    # If budget is 10000, it succeeds
    res_ok = optimize_allocation(sample_suppliers, demand=200, budget=10000.0)
    assert res_ok["is_feasible"] is True
    assert res_ok["total_cost"] <= 10000.0

    # If budget is 8000, it must be infeasible with clear explanation
    res_tight = optimize_allocation(sample_suppliers, demand=200, budget=8000.0)
    assert res_tight["is_feasible"] is False
    assert res_tight["status"] == "infeasible"
    assert any("Budget limit" in exp for exp in res_tight["explanations"])


def test_optimizer_insufficient_total_capacity(sample_suppliers):
    # Total capacity = 300 + 200 + 500 = 1000
    # Demand = 1200 > 1000
    result = optimize_allocation(sample_suppliers, demand=1200)
    assert result["is_feasible"] is False
    assert result["status"] == "infeasible"
    assert result["unmet_demand"] == 1200
    assert any("insufficient" in exp.lower() for exp in result["explanations"])


def test_optimizer_missing_supplier_price(sample_suppliers):
    # Add a supplier with null price
    corrupt_suppliers = sample_suppliers + [
        {
            "supplier_id": "SUP-BROKEN",
            "supplier_name": "Broken Co",
            "unit_price": None,
            "transport_cost": 100.0,
            "moq": 10,
            "capacity": 200,
            "currency": "INR",
        }
    ]
    result = optimize_allocation(corrupt_suppliers, demand=100)
    assert result["is_feasible"] is True
    assert "SUP-BROKEN" in result["unassigned_suppliers"]
    assert any("SUP-BROKEN" in w for w in result["warnings"])
