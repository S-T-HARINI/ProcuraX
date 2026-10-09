"""
Unit tests for Task 1: calculate_landed_cost
"""

import pytest
from procurax.cost import calculate_landed_cost
from procurax.models import Supplier


def test_calculate_landed_cost_standard():
    supplier = {
        "supplier_id": "SUP-001",
        "supplier_name": "Acme Supplies",
        "unit_price": 80.0,
        "currency": "INR",
        "transport_cost": 500.0,
    }
    result = calculate_landed_cost(supplier, quantity=100)
    assert result["supplier_id"] == "SUP-001"
    assert result["quantity"] == 100
    assert result["base_cost"] == 8000.0
    assert result["transport_cost"] == 500.0
    assert result["total_landed_cost"] == 8500.0
    assert result["cost_per_unit"] == 85.0
    assert result["currency"] == "INR"
    assert result["is_complete"] is True
    assert result["missing_cost_inputs"] == []


def test_calculate_landed_cost_missing_unit_price():
    supplier = {
        "supplier_id": "SUP-002",
        "supplier_name": "Mystery Corp",
        "unit_price": None,
        "currency": "INR",
        "transport_cost": 500.0,
    }
    result = calculate_landed_cost(supplier, quantity=50)
    assert result["total_landed_cost"] is None
    assert result["cost_per_unit"] is None
    assert "unit_price" in result["missing_cost_inputs"]
    assert result["is_complete"] is False


def test_calculate_landed_cost_missing_transport():
    supplier = {
        "supplier_id": "SUP-003",
        "supplier_name": "Partial Corp",
        "unit_price": 75.0,
        "currency": "INR",
        "transport_cost": None,
    }
    result = calculate_landed_cost(supplier, quantity=50)
    assert result["total_landed_cost"] is None
    assert "transport_cost" in result["missing_cost_inputs"]
    assert result["is_complete"] is False


def test_calculate_landed_cost_currency_conversion():
    supplier = {
        "supplier_id": "SUP-004",
        "supplier_name": "Global Trader",
        "unit_price": 10.0,
        "currency": "USD",
        "transport_cost": 50.0,
    }
    # Should raise error if converting to INR without rate
    with pytest.raises(ValueError, match="Cannot convert from USD to INR without an explicit currency conversion rate"):
        calculate_landed_cost(supplier, quantity=100, target_currency="INR")

    # Should succeed with explicit rate
    rates = {"USD_TO_INR": 83.0}
    res = calculate_landed_cost(supplier, quantity=100, target_currency="INR", currency_rates=rates)
    # 10 * 100 = 1000 USD base + 50 USD transport = 1050 USD * 83 = 87,150 INR
    assert res["total_landed_cost"] == 87150.0
    assert res["currency"] == "INR"
    assert res["cost_per_unit"] == 871.5


def test_calculate_landed_cost_with_pydantic_model():
    supplier = Supplier(
        supplier_id="SUP-005",
        supplier_name="Pydantic Vendor",
        unit_price=50.0,
        currency="INR",
        transport_cost=200.0,
    )
    result = calculate_landed_cost(supplier, quantity=20)
    assert result["total_landed_cost"] == 1200.0
    assert result["cost_per_unit"] == 60.0
