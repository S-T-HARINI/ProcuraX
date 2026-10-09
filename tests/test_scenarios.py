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


def test_scenario_transport_cost_change(baseline_suppliers):
    # Baseline: SUP-001 takes 200 units. Cost = 200 * 50 + 100 = 10100.
    # Scenario: Transport cost increases by 500 INR for SUP-001 -> new transport = 600.
    # SUP-001 cost: 200 * 50 + 600 = 10600.
    # SUP-002 cost: 200 * 55 + 100 = 11100.
    # SUP-001 is still cheaper, but total spend increases by 500.
    scenario = {
        "type": "transport_cost_change",
        "supplier_id": "SUP-001",
        "amount": 500.0,
    }
    result = simulate_scenario(baseline_suppliers, demand=200, scenario=scenario)
    assert result["is_feasible"] is True
    assert result["total_cost_delta"] == 500.0
    assert "Adjusted transport cost for SUP-001" in result["narrative_explanation"]


def test_scenario_supplier_unavailability(baseline_suppliers):
    # Baseline: SUP-001 takes all 200 units.
    # Scenario: SUP-001 is shut down / unavailable.
    scenario = {
        "type": "supplier_unavailability",
        "supplier_id": "SUP-001",
    }
    result = simulate_scenario(baseline_suppliers, demand=200, scenario=scenario)
    assert result["is_feasible"] is True
    assert result["quantity_changes"]["SUP-001"] == -200
    assert result["quantity_changes"]["SUP-002"] == 200
    assert result["total_cost_delta"] == 1000.0
    assert "Supplier SUP-001 marked UNAVAILABLE" in result["narrative_explanation"]


def test_scenario_multiplier_maps(baseline_suppliers):
    # Person 2 compatibility: price_multipliers and capacity_reductions maps
    scenario = {
        "price_multipliers": {"SUP-001": 1.25},  # 50 * 1.25 = 62.5
        "capacity_reductions": {"SUP-002": 0.50}, # 300 * 0.5 = 150
    }
    # Demand = 200. SUP-002 is cheaper (55 vs 62.5) but capped at 150.
    # SUP-002 takes 150, remaining 50 spills to SUP-001.
    result = simulate_scenario(baseline_suppliers, demand=200, scenario=scenario)
    assert result["is_feasible"] is True
    assert result["quantity_changes"]["SUP-002"] == 150
    assert result["quantity_changes"]["SUP-001"] == -150


def test_scenario_capacity_reduction_spillover(baseline_suppliers):
    scenario = {
        "type": "capacity_reduction",
        "supplier_id": "SUP-001",
        "percentage": 50.0,
    }
    result = simulate_scenario(baseline_suppliers, demand=250, scenario=scenario)
    assert result["is_feasible"] is True
    assert result["quantity_changes"]["SUP-001"] == -100
    assert result["quantity_changes"]["SUP-002"] == 100
    assert result["total_cost_delta"] > 0
    assert "Reduced capacity for SUP-001" in result["narrative_explanation"]


def test_scenario_capacity_reduction_feasibility_loss(baseline_suppliers):
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
