from typing import Optional, Protocol
from backend.app.models import (
    Claim,
    ClaimStatus,
    ExtractRequest,
    ExtractResponse,
    SupplierQuote,
)


class BaseExtractionService(Protocol):
    """
    Interface Contract for Person 1 (Gemma 4 Extraction Module).
    
    Person 1 should implement this protocol or inherit from BaseExtractionService
    and provide real model inference using Gemma 4 E2B / local endpoints.
    """
    def extract(self, request: ExtractRequest) -> ExtractResponse:
        ...


class ExtractionService:
    """
    Service wrapper delegating to either Person 1's real Gemma extraction model
    or the mock fallback service.
    """

    def __init__(self, extractor: Optional[BaseExtractionService] = None):
        self._extractor = extractor or MockExtractionService()

    def extract(self, request: ExtractRequest) -> ExtractResponse:
        return self._extractor.extract(request)


class MockExtractionService:
    """
    Mock fallback extraction service adhering strictly to the shared JSON contract.
    Returns deterministic supplier data clearly marked with is_mock=True.
    """

    def extract(self, request: ExtractRequest) -> ExtractResponse:
        source_filename = request.filename or "supplier_quotation.pdf"
        
        # Build demonstration mock suppliers following shared schema contract
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
            claims=[
                Claim(
                    field="unit_price",
                    value=80.0,
                    source_file=source_filename,
                    source_page=1,
                    source_excerpt="Unit price quoted at INR 80 per piece for bulk orders.",
                    status=ClaimStatus.EXTRACTED,
                ),
                Claim(
                    field="moq",
                    value=100,
                    source_file=source_filename,
                    source_page=1,
                    source_excerpt="Minimum Order Quantity (MOQ): 100 units.",
                    status=ClaimStatus.EXTRACTED,
                ),
                Claim(
                    field="capacity",
                    value=600,
                    source_file=source_filename,
                    source_page=1,
                    source_excerpt="Current monthly manufacturing capacity: 600 units.",
                    status=ClaimStatus.EXTRACTED,
                ),
            ],
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
                    source_page=2,
                    source_excerpt="Special volume price: INR 75/unit for MOQ > 150.",
                    status=ClaimStatus.EXTRACTED,
                ),
                Claim(
                    field="warranty_period",
                    value=None,  # null for missing numeric/field data
                    source_file=source_filename,
                    source_page=2,
                    source_excerpt="Warranty terms not specified in quote.",
                    status=ClaimStatus.MISSING,
                ),
            ],
        )

        return ExtractResponse(
            suppliers=[supplier1, supplier2],
            missing_fields_summary=["SUP-002: missing warranty_period"],
            conflicts_summary=["SUP-001 delivery_days (5 days) vs SUP-002 delivery_days (7 days)"],
            is_mock=True,
            message="Demonstration mock extraction result. Connect Gemma 4 for real document extraction.",
        )
