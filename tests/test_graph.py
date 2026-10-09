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
        "claims": [
            {
                "field": "unit_price",
                "value": 80.0,
                "source_file": "supplier_a.pdf",
                "source_page": 1,
                "source_excerpt": "Unit price quoted at INR 80.",
                "status": "extracted",
            }
        ],
    }
]


def test_generate_graph_success():
    payload = {"suppliers": SAMPLE_SUPPLIERS}
    response = client.post("/api/graph", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0
    assert len(data["edges"]) > 0

    node_types = {n["type"] for n in data["nodes"]}
    assert "supplier" in node_types
    assert "claim" in node_types
    assert "document" in node_types
    assert "decision" in node_types


def test_generate_graph_empty_suppliers():
    response = client.post("/api/graph", json={"suppliers": []})
    assert response.status_code == 400
