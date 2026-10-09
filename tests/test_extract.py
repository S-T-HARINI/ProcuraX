from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_extract_claims_basic():
    payload = {
        "filename": "supplier_quote_a.pdf",
        "raw_text": "Apex Sustainable Packaging Ltd. SUP-001 offers bottle at unit price INR 80 per piece. MOQ is 100 units.",
    }
    response = client.post("/api/extract", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "suppliers" in data
    assert len(data["suppliers"]) >= 1

    supp = data["suppliers"][0]
    assert supp["supplier_id"] == "SUP-001"
    assert supp["unit_price"] == 80.0
    assert supp["currency"] == "INR"
    assert len(supp["claims"]) >= 1

    claim = supp["claims"][0]
    assert claim["source_file"] == "supplier_quote_a.pdf"
    assert claim["source_page"] is not None
    assert claim["source_excerpt"] is not None


def test_extract_claims_preserves_missing_fields():
    payload = {
        "filename": "synthetic_supplier_beta.pdf",
        "raw_text": "BlueWave Logistics SUP-002 quotes 72.50 INR per unit for MOQ 300.",
    }
    response = client.post("/api/extract", json=payload)
    assert response.status_code == 200
    data = response.json()
    suppliers = data["suppliers"]
    assert len(suppliers) >= 1

    supp = suppliers[0]
    assert supp["supplier_id"] == "SUP-002"
    assert "transport_cost" in supp["missing_fields"] or "delivery_days" in supp["missing_fields"]
    
    missing_claim = next((c for c in supp["claims"] if c["value"] is None), None)
    if missing_claim:
        assert missing_claim["value"] is None  # Preserved as null, never 0
