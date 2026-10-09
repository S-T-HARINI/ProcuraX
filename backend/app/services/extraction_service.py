import logging
from typing import List, Optional, Protocol
from backend.app.models import (
    Claim,
    ExtractRequest,
    ExtractResponse,
    SupplierQuote,
)
from procurax.extraction.extractor import extract_supplier_data

logger = logging.getLogger("procurax.backend.extraction")


class BaseExtractionService(Protocol):
    """
    Interface Contract for Person 1 (Gemma 4 Extraction Module).
    """
    def extract(self, request: ExtractRequest) -> ExtractResponse:
        ...


class ExtractionService:
    """
    Service layer bridging API requests to Person 1's Gemma 4 extraction module
    and mock fallback.
    """

    def extract(self, request: ExtractRequest) -> ExtractResponse:
        filename = request.filename or "supplier_quotation.pdf"
        raw_text = request.raw_text or ""
        if request.parsed_pages:
            raw_text += "\n" + "\n".join([f"--- Page {p.page_number} ---\n{p.text}" for p in request.parsed_pages])

        if not raw_text.strip():
            raw_text = f"Demonstration quotation text for {filename}."

        source_pages_map = None
        if request.parsed_pages:
            source_pages_map = {p.page_number: p.text for p in request.parsed_pages}

        # Call Person 1's extract_supplier_data implementation
        contract_dict = extract_supplier_data(
            document_text=raw_text,
            source_file=filename,
            source_pages=source_pages_map,
            use_mock=request.use_mock,
            model=request.model,
            allow_fallback=True,
        )

        # Convert dict to SupplierQuote model
        supplier_obj = SupplierQuote.model_validate(contract_dict)
        
        # Check if fallback was triggered or mock requested
        metadata = contract_dict.get("metadata", {})
        is_mock_flag = (
            request.use_mock
            or metadata.get("is_synthetic", False)
            or metadata.get("fallback_triggered", False)
            or "MOCK" in str(metadata.get("extraction_engine", "")).upper()
        )

        missing_summary = [f"{supplier_obj.supplier_id}: missing {f}" for f in supplier_obj.missing_fields]
        conflicts_summary = [f"{supplier_obj.supplier_id}: conflicting {f}" for f in supplier_obj.conflicting_fields]

        return ExtractResponse(
            suppliers=[supplier_obj],
            missing_fields_summary=missing_summary,
            conflicts_summary=conflicts_summary,
            is_mock=is_mock_flag,
            message="Supplier quotation extraction complete.",
        )
