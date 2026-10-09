from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

SAMPLE_SUPPLIERS = [
    {
        "supplier_id": "SUP-001",
        "supplier_name": "Apex Eco Solutions",
        "product_name": "Reusable Bottle",
        "unit_price": 80.0,
        "currency": "INR",
        "moq": 100,
        "capacity": 600,
        "delivery_days": 5,
        "transport_cost": 500.0,
        "sustainability_claims": [],
        "missing_fields": [],
        "claims": [],
    },
    {
        "supplier_id": "SUP-002",
        "supplier_name": "GreenPoly Tech Ltd",
        "product_name": "Reusable Bottle",
        "unit_price": 75.0,
        "currency": "INR",
        "moq": 150,
        "capacity": 400,
        "delivery_days": 7,
        "transport_cost": 700.0,
        "sustainability_claims": [],
        "missing_fields": [],
        "claims": [],
    },
]


def test_optimize_success():
    payload = {
        "suppliers": SAMPLE_SUPPLIERS,
        "target_demand": 500,
        "budget_limit": 50000.0,
    }
    response = client.post("/api/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "optimal"
    assert data["total_allocated_quantity"] == 500
    assert data["total_landed_cost"] > 0
    assert len(data["allocations"]) > 0


def test_optimize_with_scenarios():
    payload = {
        "suppliers": SAMPLE_SUPPLIERS,
        "target_demand": 500,
        "scenario": {
            "type": "price_increase",
            "supplier_id": "SUP-002",
            "percentage": 50.0,
        },
    }
    response = client.post("/api/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_allocated_quantity"] == 500
    assert data["scenario_impact"] is not None


def test_optimize_budget_exceeded():
    payload = {
        "suppliers": SAMPLE_SUPPLIERS,
        "target_demand": 500,
        "budget_limit": 10000.0,  # Very low budget
    }
    response = client.post("/api/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "infeasible"
    assert len(data["explanations"]) > 0 or len(data["warnings"]) > 0
    assert any("budget" in str(item).lower() for item in data["explanations"] + data["warnings"])


def test_optimize_infeasible_capacity():
    payload = {
        "suppliers": SAMPLE_SUPPLIERS,
        "target_demand": 2000,  # Combined capacity is only 1000
    }
    response = client.post("/api/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "infeasible"
    assert data["unmet_demand"] > 0
    assert len(data["explanations"]) > 0 or len(data["warnings"]) > 0


def test_optimize_invalid_request():
    # Pydantic schema validation failure (target_demand <= 0) returns 422 Unprocessable Entity
    response = client.post("/api/optimize", json={"suppliers": [], "target_demand": 0})
    assert response.status_code == 422

    # Business validation failure (empty suppliers with valid target_demand) returns 400 Bad Request
    response_400 = client.post("/api/optimize", json={"suppliers": [], "target_demand": 100})
    assert response_400.status_code == 400
