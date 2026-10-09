from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_extract_claims_basic():
    payload = {
        "filename": "supplier_quote_a.pdf",
        "raw_text": "Apex Eco Solutions offers Stainless Steel Bottle 750ml at unit price INR 80 per piece. Minimum order quantity (MOQ) is 100 units.",
    }
    response = client.post("/api/extract", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "suppliers" in data
    assert len(data["suppliers"]) >= 1
    assert data["is_mock"] is True

    # Validate JSON contract compliance
    supp = data["suppliers"][0]
    assert supp["supplier_id"] == "SUP-001"
    assert supp["unit_price"] == 80.0
    assert supp["currency"] == "INR"
    assert len(supp["claims"]) >= 1

    claim = supp["claims"][0]
    assert claim["source_file"] == "supplier_quote_a.pdf"
    assert claim["source_page"] is not None
    assert claim["source_excerpt"] is not None
    assert claim["status"] in ["extracted", "verified", "conflicting", "ambiguous", "missing"]


def test_extract_claims_preserves_missing_fields():
    payload = {
        "filename": "supplier_b.pdf",
        "raw_text": "GreenPoly Tech quotes 75 INR per unit for MOQ 150.",
    }
    response = client.post("/api/extract", json=payload)
    assert response.status_code == 200
    data = response.json()
    suppliers = data["suppliers"]
    
    # Check that supplier missing fields have null values and are noted in missing_fields_summary
    supp2 = next((s for s in suppliers if s["supplier_id"] == "SUP-002"), None)
    assert supp2 is not None
    assert "warranty_period" in supp2["missing_fields"]
    
    missing_claim = next((c for c in supp2["claims"] if c["field"] == "warranty_period"), None)
    assert missing_claim is not None
    assert missing_claim["value"] is None  # Must be null, never 0
