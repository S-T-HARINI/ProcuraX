import io
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_upload_csv_success():
    csv_content = "Supplier,Product,UnitPrice,Capacity\nApex,Bottle,80.0,600\n"
    response = client.post(
        "/api/documents/upload",
        files={"file": ("supplier_quote.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "supplier_quote.csv"
    assert data["file_type"] == "csv"
    assert data["total_pages"] >= 1
    assert "Apex,Bottle,80.0,600" in data["raw_text"]


def test_upload_empty_file():
    response = client.post(
        "/api/documents/upload",
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_unsupported_format():
    response = client.post(
        "/api/documents/upload",
        files={"file": ("unsupported.docx", io.BytesIO(b"dummy data"), "application/vnd.word")},
    )
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()
