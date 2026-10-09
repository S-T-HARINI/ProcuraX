import os
import re
import logging
from typing import Optional, Protocol, List
from backend.app.models import (
    Claim,
    ClaimStatus,
    ExtractRequest,
    ExtractResponse,
    SupplierQuote,
)

logger = logging.getLogger("procurax.extraction")


class BaseExtractionService(Protocol):
    """
    Interface Contract for Person 1 (Gemma 4 Extraction Module).
    
    Person 1 implements this protocol or inherits from BaseExtractionService
    to provide real model inference using Gemma 4 E2B / local endpoints.
    """
    def extract(self, request: ExtractRequest) -> ExtractResponse:
        ...


class ExtractionService:
    """
    Service wrapper delegating to Person 1's real Gemma extraction model
    or falling back seamlessly to MockExtractionService.
    """

    def __init__(self, extractor: Optional[BaseExtractionService] = None):
        self._extractor = extractor or self._resolve_extractor()

    def _resolve_extractor(self) -> BaseExtractionService:
        # Check if Person 1's Gemma extraction endpoint environment variable is set
        gemma_url = os.getenv("GEMMA_API_URL")
        if gemma_url:
            try:
                return RemoteGemmaExtractionService(api_url=gemma_url)
            except Exception as err:
                logger.warning(f"Could not initialize RemoteGemmaExtractionService ({err}). Using mock fallback.")
        return MockExtractionService()

    def extract(self, request: ExtractRequest) -> ExtractResponse:
        try:
            return self._extractor.extract(request)
        except Exception as err:
            logger.error(f"Extraction error with primary extractor: {err}. Falling back to mock extraction.")
            return MockExtractionService().extract(request)


class RemoteGemmaExtractionService:
    """
    Client for Person 1's hosted or local Gemma 4 inference service.
    """

    def __init__(self, api_url: str):
        self.api_url = api_url

    def extract(self, request: ExtractRequest) -> ExtractResponse:
        import httpx
        # Send extraction request to Person 1's Gemma endpoint
        response = httpx.post(f"{self.api_url}/extract", json=request.model_dump(), timeout=15.0)
        response.raise_for_status()
        data = response.json()
        return ExtractResponse(**data)


class MockExtractionService:
    """
    Deterministic mock extraction service adhering strictly to the shared JSON contract.
    Returns extracted supplier data clearly marked with is_mock=True.
    Supports dynamic text scanning when raw_text or parsed_pages are provided.
    """

    def extract(self, request: ExtractRequest) -> ExtractResponse:
        source_filename = request.filename or "supplier_quotation.pdf"
        raw_text = request.raw_text or ""
        
        if request.parsed_pages:
            raw_text += "\n" + "\n".join([f"Page {p.page_number}: {p.text}" for p in request.parsed_pages])

        # Default demonstration fallback suppliers matching shared schema
        supplier1_claims = [
            Claim(
                field="unit_price",
                value=80.0,
                source_file=source_filename,
                source_page=1,
                source_excerpt=self._find_excerpt(raw_text, r"unit price|price", "Unit price quoted at INR 80 per piece for bulk orders."),
                status=ClaimStatus.EXTRACTED,
            ),
            Claim(
                field="moq",
                value=100,
                source_file=source_filename,
                source_page=1,
                source_excerpt=self._find_excerpt(raw_text, r"moq|minimum order", "Minimum Order Quantity (MOQ): 100 units."),
                status=ClaimStatus.EXTRACTED,
            ),
            Claim(
                field="capacity",
                value=600,
                source_file=source_filename,
                source_page=1,
                source_excerpt=self._find_excerpt(raw_text, r"capacity|volume", "Current monthly manufacturing capacity: 600 units."),
                status=ClaimStatus.EXTRACTED,
            ),
        ]

        supplier1 = SupplierQuote(
            supplier_id="SUP-001",
            supplier_name="Apex Eco Solutions",
            product_name="Reusable Stainless Steel Bottle 750ml",
            unit_price=80.0,
            currency="INR",
            moq=100,
            capacity=600,
            delivery_days=5,
            transport_cost=500.0,
            sustainability_claims=["100% Recyclable Packaging", "ISO 14001 Certified"],
            missing_fields=[],
            claims=supplier1_claims,
        )

        supplier2 = SupplierQuote(
            supplier_id="SUP-002",
            supplier_name="GreenPoly Tech Ltd",
            product_name="Reusable Stainless Steel Bottle 750ml",
            unit_price=75.0,
            currency="INR",
            moq=150,
            capacity=400,
            delivery_days=7,
            transport_cost=700.0,
            sustainability_claims=["BPA Free", "Zero Plastics"],
            missing_fields=["warranty_period"],
            claims=[
                Claim(
                    field="unit_price",
                    value=75.0,
                    source_file=source_filename,
                    source_page=min(2, max(1, len(request.parsed_pages) if request.parsed_pages else 1)),
                    source_excerpt="Special volume price: INR 75/unit for MOQ > 150.",
                    status=ClaimStatus.EXTRACTED,
                ),
                Claim(
                    field="warranty_period",
                    value=None,  # null for unknown/missing values
                    source_file=source_filename,
                    source_page=1,
                    source_excerpt="Warranty terms not specified in quotation document.",
                    status=ClaimStatus.MISSING,
                ),
            ],
        )

        return ExtractResponse(
            suppliers=[supplier1, supplier2],
            missing_fields_summary=["SUP-002: missing warranty_period"],
            conflicts_summary=["SUP-001 delivery_days (5 days) vs SUP-002 delivery_days (7 days)"],
            is_mock=True,
            message="Mock extraction fallback result. Connect Gemma 4 service for live document extraction.",
        )

    def _find_excerpt(self, text: str, pattern: str, fallback: str) -> str:
        if not text:
            return fallback
        match = re.search(f".{{0,30}}{pattern}.{{0,40}}", text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
        return fallback
