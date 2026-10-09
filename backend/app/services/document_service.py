import csv
import io
from typing import Tuple
from backend.app.models import DocumentPage, DocumentParseResponse


class DocumentService:
    @staticmethod
    def parse_document(file_bytes: bytes, filename: str) -> DocumentParseResponse:
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        
        if ext == "pdf":
            return DocumentService._parse_pdf(file_bytes, filename)
        elif ext == "csv":
            return DocumentService._parse_csv(file_bytes, filename)
        elif ext in ["xlsx", "xls"]:
            return DocumentService._parse_excel(file_bytes, filename)
        else:
            raise ValueError(f"Unsupported file format '.{ext}'. Supported formats: PDF, CSV, XLSX.")

    @staticmethod
    def _parse_pdf(file_bytes: bytes, filename: str) -> DocumentParseResponse:
        pages: list[DocumentPage] = []
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages.append(DocumentPage(page_number=i + 1, text=text.strip()))
        except Exception:
            # Fallback if pypdf fails or not fully readable
            text_content = file_bytes.decode("utf-8", errors="ignore")
            pages.append(DocumentPage(page_number=1, text=text_content.strip()))

        raw_text = "\n\n".join([f"--- Page {p.page_number} ---\n{p.text}" for p in pages])
        return DocumentParseResponse(
            filename=filename,
            file_type="pdf",
            total_pages=len(pages),
            pages=pages,
            raw_text=raw_text,
        )

    @staticmethod
    def _parse_csv(file_bytes: bytes, filename: str) -> DocumentParseResponse:
        content = file_bytes.decode("utf-8", errors="ignore")
        lines = content.splitlines()
        
        pages: list[DocumentPage] = []
        page_size = 50  # group rows into readable page blocks
        for i in range(0, max(1, len(lines)), page_size):
            chunk_lines = lines[i:i + page_size]
            page_num = (i // page_size) + 1
            pages.append(DocumentPage(page_number=page_num, text="\n".join(chunk_lines)))

        return DocumentParseResponse(
            filename=filename,
            file_type="csv",
            total_pages=len(pages),
            pages=pages,
            raw_text=content,
        )

    @staticmethod
    def _parse_excel(file_bytes: bytes, filename: str) -> DocumentParseResponse:
        pages: list[DocumentPage] = []
        try:
            import openpyxl
            wb = openpyxl.load_workbook(filename=io.BytesIO(file_bytes), data_only=True)
            for i, sheet_name in enumerate(wb.sheetnames):
                sheet = wb[sheet_name]
                rows_text = []
                for row in sheet.iter_rows(values_only=True):
                    row_vals = [str(val) if val is not None else "" for val in row]
                    if any(row_vals):
                        rows_text.append(", ".join(row_vals))
                pages.append(DocumentPage(page_number=i + 1, text=f"Sheet: {sheet_name}\n" + "\n".join(rows_text)))
        except Exception:
            pages.append(DocumentPage(page_number=1, text=file_bytes.decode("utf-8", errors="ignore")))

        raw_text = "\n\n".join([f"--- Page {p.page_number} ---\n{p.text}" for p in pages])
        return DocumentParseResponse(
            filename=filename,
            file_type="xlsx",
            total_pages=len(pages),
            pages=pages,
            raw_text=raw_text,
        )
