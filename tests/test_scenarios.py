"""
Unit tests for Task 3: simulate_scenario
"""

import pytest
from procurax.scenarios import simulate_scenario


@pytest.fixture
def baseline_suppliers():
    return [
        {
            "supplier_id": "SUP-001",
            "supplier_name": "Supplier 1",
            "unit_price": 50.0,
            "transport_cost": 100.0,
            "moq": 50,
            "capacity": 300,
            "currency": "INR",
        },
        {
            "supplier_id": "SUP-002",
            "supplier_name": "Supplier 2",
            "unit_price": 55.0,
            "transport_cost": 100.0,
            "moq": 50,
            "capacity": 300,
            "currency": "INR",
        },
    ]


def test_scenario_price_increase_reallocation(baseline_suppliers):
    # Demand = 200.
    # Baseline: SUP-001 is cheaper (50 vs 55), takes all 200 units. Total = 200*50 + 100 = 10100.
    # Scenario: SUP-001 price increases by 20% -> 60.0.
    # Now SUP-002 (55) is cheaper than SUP-001 (60), so volume should reallocate to SUP-002!
    scenario = {
        "type": "price_increase",
        "supplier_id": "SUP-001",
        "percentage": 20.0,
    }
    result = simulate_scenario(baseline_suppliers, demand=200, scenario=scenario)

    assert result["is_feasible"] is True
    assert result["baseline_status"] == "optimal"
    assert result["scenario_status"] == "optimal"

    # SUP-001 lost 200, SUP-002 gained 200
    assert result["quantity_changes"]["SUP-001"] == -200
    assert result["quantity_changes"]["SUP-002"] == 200

    # New cost: 200 * 55 + 100 = 11100. Delta = 11100 - 10100 = +1000
    assert result["total_cost_delta"] == 1000.0
    assert "Volume reallocation" in result["narrative_explanation"]


def test_scenario_capacity_reduction_spillover(baseline_suppliers):
    # Demand = 250.
    # Baseline: SUP-001 (cap 300) takes all 250 units.
    # Scenario: SUP-001 capacity reduced by 50% -> 150 units.
    # SUP-001 can only take 150 units; remaining 100 must spill over to SUP-002.
    scenario = {
        "type": "capacity_reduction",
        "supplier_id": "SUP-001",
        "percentage": 50.0,
    }
    result = simulate_scenario(baseline_suppliers, demand=250, scenario=scenario)

    assert result["is_feasible"] is True
    assert result["quantity_changes"]["SUP-001"] == -100
    assert result["quantity_changes"]["SUP-002"] == 100

    # SUP-002 has higher unit price, so cost increases
    assert result["total_cost_delta"] > 0
    assert "Reduced capacity for SUP-001" in result["narrative_explanation"]


def test_scenario_capacity_reduction_feasibility_loss(baseline_suppliers):
    # Total baseline capacity = 600. Demand = 500.
    # Scenario: SUP-001 capacity reduced by 90% (to 30). Total capacity = 30 + 300 = 330 < 500.
    scenario = {
        "type": "capacity_reduction",
        "supplier_id": "SUP-001",
        "percentage": 90.0,
    }
    result = simulate_scenario(baseline_suppliers, demand=500, scenario=scenario)

    assert result["baseline_status"] == "optimal"
    assert result["is_feasible"] is False
    assert result["scenario_status"] == "infeasible"
    assert "FEASIBILITY LOSS" in result["narrative_explanation"]


def test_scenario_compound(baseline_suppliers):
    # Compound: SUP-001 price up 10% AND SUP-002 capacity reduced by 50%
    scenario = {
        "type": "compound",
        "scenarios": [
            {"type": "price_increase", "supplier_id": "SUP-001", "percentage": 10.0},
            {"type": "capacity_reduction", "supplier_id": "SUP-002", "percentage": 50.0},
        ],
    }
    result = simulate_scenario(baseline_suppliers, demand=200, scenario=scenario)
    assert result["is_feasible"] is True
    assert result["total_cost_delta"] > 0
