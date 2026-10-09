from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_end_to_end_workflow_basic():
    payload = {
        "document_filename": "quotation_alpha.pdf",
        "document_text": """
        Supplier: Apex Sustainable Packaging Ltd.
        Supplier ID: SUP-001
        Unit Price: 80.00 INR per bottle
        Minimum Order Quantity (MOQ): 100 units
        Production Monthly Capacity: 600 units
        Transportation & Freight: 500.00 INR flat charge
        """,
        "target_demand": 500,
        "budget_limit": 50000.0,
        "use_mock_extraction": True,
    }
    response = client.post("/api/workflow", json=payload)
    assert response.status_code == 200
    data = response.json()

    # 1. Verify Document Info
    assert "document" in data
    assert data["document"]["filename"] == "quotation_alpha.pdf"

    # 2. Verify Extraction Response
    assert "extraction" in data
    extract = data["extraction"]
    assert len(extract["suppliers"]) >= 1
    assert extract["suppliers"][0]["supplier_id"] == "SUP-001"
    assert extract["suppliers"][0]["unit_price"] == 80.0

    # 3. Verify Optimization Response
    assert "optimization" in data
    opt = data["optimization"]
    assert opt["status"] == "optimal"
    assert opt["total_allocated_quantity"] == 500
    assert opt["total_landed_cost"] > 0
    assert len(opt["allocations"]) >= 1

    # 4. Verify Evidence Graph Response
    assert "graph" in data
    graph = data["graph"]
    assert len(graph["nodes"]) > 0
    assert len(graph["edges"]) > 0
    node_types = {n["type"] for n in graph["nodes"]}
    assert "supplier" in node_types or "claim" in node_types

    # 5. Verify Executive Summary
    assert "summary" in data
    assert "ProcuraX Sourcing Report" in data["summary"]


def test_end_to_end_workflow_with_scenario():
    payload = {
        "document_filename": "quotation_scenario.pdf",
        "document_text": "Apex Sustainable Packaging Ltd. SUP-001 Unit Price 80.00 INR MOQ 100 Capacity 600 Freight 500.00",
        "target_demand": 400,
        "scenario": {
            "type": "price_increase",
            "supplier_id": "SUP-001",
            "percentage": 20.0,
        },
        "use_mock_extraction": True,
    }
    response = client.post("/api/workflow", json=payload)
    assert response.status_code == 200
    data = response.json()
    opt = data["optimization"]
    assert opt["scenario_impact"] is not None
    assert opt["scenario_impact"]["scenario_type"] == "price_increase"


def test_end_to_end_workflow_invalid_demand():
    payload = {
        "target_demand": 0,  # Invalid demand <= 0
    }
    response = client.post("/api/workflow", json=payload)
    assert response.status_code == 422
