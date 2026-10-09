from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_extract_claims():
    payload = {
        "filename": "supplier_a.pdf",
        "raw_text": "Supplier A offers bottle at 80 INR MOQ 100 capacity 600 delivery 5 days.",
    }
    response = client.post("/api/extract", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "suppliers" in data
    assert len(data["suppliers"]) >= 1
    assert data["is_mock"] is True
    
    # Check JSON contract compliance
    first_supp = data["suppliers"][0]
    assert "supplier_id" in first_supp
    assert "unit_price" in first_supp
    assert "claims" in first_supp
    assert len(first_supp["claims"]) >= 1
    
    first_claim = first_supp["claims"][0]
    assert "field" in first_claim
    assert "source_file" in first_claim
    assert "source_excerpt" in first_claim
    assert first_claim["status"] in ["extracted", "verified", "conflicting", "ambiguous", "missing"]
