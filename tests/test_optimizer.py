"""
Unit tests for Task 2: optimize_allocation
"""

import json
from pathlib import Path
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
    result = optimize_allocation(sample_suppliers, demand=200)
    assert result["is_feasible"] is True
    assert result["status"] == "optimal"
    assert result["allocated_demand"] == 200
    assert result["unmet_demand"] == 0
    assert len(result["allocations"]) >= 1
    alloc_ids = [a["supplier_id"] for a in result["allocations"]]
    assert "SUP-002" in alloc_ids
    assert result["total_cost"] == 9500.0

    breakdown = result["supplier_breakdown"]
    assert len(breakdown) == 3
    b_map = {b["supplier_id"]: b for b in breakdown}
    assert b_map["SUP-002"]["status"] == "allocated"
    assert b_map["SUP-001"]["status"] == "unassigned"


def test_optimizer_capacity_and_split(sample_suppliers):
    result = optimize_allocation(sample_suppliers, demand=400)
    assert result["is_feasible"] is True
    assert result["allocated_demand"] == 400
    allocations = {a["supplier_id"]: a["allocated_quantity"] for a in result["allocations"]}
    assert allocations.get("SUP-002") == 200
    assert allocations.get("SUP-001") == 200
    assert result["total_cost"] == 19700.0


def test_optimizer_moq_enforcement(sample_suppliers):
    result = optimize_allocation(sample_suppliers, demand=30)
    assert result["is_feasible"] is True
    assert result["allocated_demand"] == 30
    assert len(result["allocations"]) == 1
    assert result["allocations"][0]["supplier_id"] == "SUP-003"
    assert result["allocations"][0]["allocated_quantity"] == 30


def test_optimizer_budget_constraint(sample_suppliers):
    res_ok = optimize_allocation(sample_suppliers, demand=200, budget=10000.0)
    assert res_ok["is_feasible"] is True
    assert res_ok["total_cost"] <= 10000.0

    res_tight = optimize_allocation(sample_suppliers, demand=200, budget=8000.0)
    assert res_tight["is_feasible"] is False
    assert res_tight["status"] == "infeasible"
    assert any("Budget limit" in exp for exp in res_tight["explanations"])


def test_optimizer_insufficient_total_capacity(sample_suppliers):
    result = optimize_allocation(sample_suppliers, demand=1200)
    assert result["is_feasible"] is False
    assert result["status"] == "infeasible"
    assert result["unmet_demand"] == 1200
    assert any("insufficient" in exp.lower() for exp in result["explanations"])


def test_optimizer_missing_supplier_price(sample_suppliers):
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
    assert "SUP-BROKEN" in result["exclusion_reasons"]
    assert "unit_price is missing/null" in result["exclusion_reasons"]["SUP-BROKEN"]


def test_optimizer_unavailable_supplier(sample_suppliers):
    result = optimize_allocation(sample_suppliers, demand=200, unavailable_suppliers=["SUP-002"])
    assert result["is_feasible"] is True
    alloc_ids = [a["supplier_id"] for a in result["allocations"]]
    assert "SUP-002" not in alloc_ids
    assert "SUP-001" in alloc_ids
    assert "SUP-002" in result["exclusion_reasons"]


def test_optimizer_per_unit_transport(sample_suppliers):
    suppliers = [
        {
            "supplier_id": "SUP-FLAT",
            "supplier_name": "Flat Transport",
            "unit_price": 50.0,
            "transport_cost": 200.0,
            "transport_cost_type": "fixed_per_shipment",
            "moq": 10,
            "capacity": 200,
            "currency": "INR",
        },
        {
            "supplier_id": "SUP-UNIT",
            "supplier_name": "Unit Transport",
            "unit_price": 48.0,
            "transport_cost": 5.0,
            "transport_cost_type": "per_unit",
            "moq": 10,
            "capacity": 200,
            "currency": "INR",
        },
    ]
    result = optimize_allocation(suppliers, demand=100)
    assert result["is_feasible"] is True
    assert result["allocations"][0]["supplier_id"] == "SUP-FLAT"
    assert result["total_cost"] == 5200.0


def test_optimizer_deterministic(sample_suppliers):
    # Verifies requirement: results are strictly deterministic for the same input
    res1 = optimize_allocation(sample_suppliers, demand=350, budget=25000.0)
    res2 = optimize_allocation(sample_suppliers, demand=350, budget=25000.0)

    assert res1["total_cost"] == res2["total_cost"]
    assert res1["allocated_demand"] == res2["allocated_demand"]
    assert [a["allocated_quantity"] for a in res1["allocations"]] == [a["allocated_quantity"] for a in res2["allocations"]]


def test_synthetic_dataset_solver():
    # Test loading and solving synthetic benchmark dataset
    dataset_file = Path("data/synthetic_demo_suppliers.json")
    assert dataset_file.exists()
    with open(dataset_file, "r", encoding="utf-8") as f:
        suppliers = json.load(f)

    res = optimize_allocation(suppliers, demand=600, budget=50000.0)
    assert res["is_feasible"] is True
    assert res["allocated_demand"] == 600
    assert res["total_cost"] == 46550.0

    # Verify SUP-004 is excluded due to missing unit price
    assert "SUP-004" in res["exclusion_reasons"]
