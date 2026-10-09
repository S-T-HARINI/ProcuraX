import io
import openpyxl
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


def test_upload_xlsx_success():
    # Create valid in-memory Excel file using openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Quotation"
    ws.append(["Supplier", "Product", "Unit Price", "MOQ"])
    ws.append(["Apex Eco", "Stainless Bottle 750ml", 80.0, 100])
    
    excel_bytes = io.BytesIO()
    wb.save(excel_bytes)
    excel_bytes.seek(0)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("quote.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "quote.xlsx"
    assert data["file_type"] == "xlsx"
    assert data["total_pages"] == 1
    assert "Sheet: Quotation" in data["pages"][0]["text"]
    assert "Apex Eco" in data["raw_text"]


def test_upload_empty_file():
    response = client.post(
        "/api/documents/upload",
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_whitespace_file():
    response = client.post(
        "/api/documents/upload",
        files={"file": ("spaces.csv", io.BytesIO(b"   \n\n  \t "), "text/csv")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower() or "whitespace" in response.json()["detail"].lower()


def test_upload_corrupted_pdf():
    corrupted_pdf_bytes = b"%PDF-1.4 Corrupted binary garbage content without valid header or trailer"
    response = client.post(
        "/api/documents/upload",
        files={"file": ("corrupted.pdf", io.BytesIO(corrupted_pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 400
    assert "corrupted" in response.json()["detail"].lower() or "failed to parse" in response.json()["detail"].lower()


def test_upload_unsupported_format():
    response = client.post(
        "/api/documents/upload",
        files={"file": ("quote.docx", io.BytesIO(b"word document bytes"), "application/vnd.word")},
    )
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()
