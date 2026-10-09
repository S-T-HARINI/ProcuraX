"""Clearly labelled mock fallback and synthetic demonstration datasets for ProcuraX.

All data in this module is explicitly synthetic and intended for:
1. Offline testing when Gemma 4/Ollama is not running.
2. Teammates (Persons 2 & 3) requiring deterministic supplier data for API and optimization testing.

Rules:
- Labeled synthetic demonstration data.
- Does not claim mock data came from a real supplier document.
- Distinguishes extracted claims from independently verified facts.
"""

from typing import Any, Dict, Optional, Union
from procurax.extraction.schema import Claim, SupplierQuotation


SYNTHETIC_DOC_ALPHA = """--- Page 1 ---
[DEMO QUOTATION - SYNTHETIC DATA]
Quotation Reference: SYN-ALPHA-2026-01
Supplier: Apex Sustainable Packaging Ltd.
Supplier ID: SUP-001
Date: 2026-03-01

Item: Reusable Industrial Bottle (500ml)
Pricing Details:
- Base Unit Price: 80.00 INR per bottle
- Minimum Order Quantity (MOQ): 100 units
- Production Monthly Capacity: 600 units
- Standard Delivery Lead Time: 5 business days
- Fixed Transportation & Freight: 500.00 INR flat charge per shipment

Discounts & Volume:
- Tiered discount: 5% off on orders exceeding 500 units.

Sustainability Certification:
- Certified 100% Ocean Bound Recycled HDPE
- Closed-loop manufacturing process
"""

SYNTHETIC_DOC_BETA = """--- Page 1 ---
[DEMO QUOTATION - SYNTHETIC DATA]
Quotation Reference: SYN-BETA-2026-02
Supplier: BlueWave Logistics & Supplies
Supplier ID: SUP-002
Date: 2026-03-02

Item: Reusable Industrial Bottle (500ml)
Pricing Details:
- Unit Price: 72.50 INR per bottle
- Minimum Order Quantity (MOQ): 300 units
- Monthly Supply Capacity: 1000 units
- Delivery Lead Time: 5 to 14 business days (variable depending on transport backlog)
- Freight / Shipping: To be determined upon delivery destination (Not Included)

Sustainability Claims:
- Recyclable resin blend (Code 2)
"""

SYNTHETIC_DOC_GAMMA = """--- Page 1 ---
[DEMO QUOTATION - SYNTHETIC DATA]
Quotation Reference: SYN-GAMMA-2026-03
Supplier: GreenSource Manufacturing Co.
Supplier ID: SUP-003
Date: 2026-03-03

Item: Reusable Industrial Bottle (500ml)
Pricing Details:
- Standard Unit Price: 85.00 INR per bottle
- Urgent Dispatch Unit Price: 95.00 INR per bottle (contradictory rush pricing stated)
- Minimum Order Quantity (MOQ): 50 units
- Maximum Production Capacity: 400 units
- Delivery Lead Time: 3 business days
- Freight & Delivery Charge: 350.00 INR

Discounts:
- No volume discounts offered.
"""


def create_mock_supplier_alpha(source_file: str = "synthetic_supplier_alpha.pdf") -> SupplierQuotation:
    """Generate deterministic synthetic quotation for Supplier Alpha (Clean/Standard)."""
    return SupplierQuotation(
        supplier_id="SUP-001",
        supplier_name="Apex Sustainable Packaging Ltd.",
        product_name="Reusable Industrial Bottle (500ml)",
        unit_price=80.0,
        currency="INR",
        moq=100,
        capacity=600,
        delivery_days=5,
        transport_cost=500.0,
        discount_terms="5% off on orders exceeding 500 units.",
        sustainability_claims=[
            "Certified 100% Ocean Bound Recycled HDPE",
            "Closed-loop manufacturing process"
        ],
        missing_fields=[],
        ambiguous_fields=[],
        conflicting_fields=[],
        claims=[
            Claim(
                field="unit_price",
                value=80.0,
                source_file=source_file,
                source_page=1,
                source_excerpt="Base Unit Price: 80.00 INR per bottle",
                status="extracted",
                is_verified_fact=False
            ),
            Claim(
                field="moq",
                value=100,
                source_file=source_file,
                source_page=1,
                source_excerpt="Minimum Order Quantity (MOQ): 100 units",
                status="extracted",
                is_verified_fact=False
            ),
            Claim(
                field="capacity",
                value=600,
                source_file=source_file,
                source_page=1,
                source_excerpt="Production Monthly Capacity: 600 units",
                status="extracted",
                is_verified_fact=False
            ),
            Claim(
                field="delivery_days",
                value=5,
                source_file=source_file,
                source_page=1,
                source_excerpt="Standard Delivery Lead Time: 5 business days",
                status="extracted",
                is_verified_fact=False
            ),
            Claim(
                field="transport_cost",
                value=500.0,
                source_file=source_file,
                source_page=1,
                source_excerpt="Fixed Transportation & Freight: 500.00 INR flat charge per shipment",
                status="extracted",
                is_verified_fact=False
            )
        ],
        metadata={
            "extraction_engine": "MOCK_FALLBACK (Synthetic Demonstration Data)",
            "is_synthetic": True,
            "demo_scenario": "Standard baseline supplier"
        }
    )


def create_mock_supplier_beta(source_file: str = "synthetic_supplier_beta.pdf") -> SupplierQuotation:
    """Generate deterministic synthetic quotation for Supplier Beta (Missing Freight & Ambiguous Delivery)."""
    return SupplierQuotation(
        supplier_id="SUP-002",
        supplier_name="BlueWave Logistics & Supplies",
        product_name="Reusable Industrial Bottle (500ml)",
        unit_price=72.50,
        currency="INR",
        moq=300,
        capacity=1000,
        delivery_days=None,  # Null because ambiguous/uncertain
        transport_cost=None,  # Null because missing/unspecified
        discount_terms=None,
        sustainability_claims=["Recyclable resin blend (Code 2)"],
        missing_fields=["delivery_days", "transport_cost"],
        ambiguous_fields=["delivery_days"],
        conflicting_fields=[],
        claims=[
            Claim(
                field="unit_price",
                value=72.50,
                source_file=source_file,
                source_page=1,
                source_excerpt="Unit Price: 72.50 INR per bottle",
                status="extracted",
                is_verified_fact=False
            ),
            Claim(
                field="moq",
                value=300,
                source_file=source_file,
                source_page=1,
                source_excerpt="Minimum Order Quantity (MOQ): 300 units",
                status="extracted",
                is_verified_fact=False
            ),
            Claim(
                field="delivery_days",
                value="5 to 14 business days",
                source_file=source_file,
                source_page=1,
                source_excerpt="Delivery Lead Time: 5 to 14 business days (variable depending on transport backlog)",
                status="ambiguous",
                notes="Wide delivery window dependent on external backlog",
                is_verified_fact=False
            ),
            Claim(
                field="transport_cost",
                value=None,
                source_file=source_file,
                source_page=1,
                source_excerpt="Freight / Shipping: To be determined upon delivery destination (Not Included)",
                status="extracted",
                notes="Freight not quoted by supplier; pending destination",
                is_verified_fact=False
            )
        ],
        metadata={
            "extraction_engine": "MOCK_FALLBACK (Synthetic Demonstration Data)",
            "is_synthetic": True,
            "demo_scenario": "Incomplete quotation with ambiguous delivery and missing freight"
        }
    )


def create_mock_supplier_gamma(source_file: str = "synthetic_supplier_gamma.pdf") -> SupplierQuotation:
    """Generate deterministic synthetic quotation for Supplier Gamma (Conflicting Rush Pricing)."""
    return SupplierQuotation(
        supplier_id="SUP-003",
        supplier_name="GreenSource Manufacturing Co.",
        product_name="Reusable Industrial Bottle (500ml)",
        unit_price=85.0,
        currency="INR",
        moq=50,
        capacity=400,
        delivery_days=3,
        transport_cost=350.0,
        discount_terms=None,
        sustainability_claims=[],
        missing_fields=[],
        ambiguous_fields=[],
        conflicting_fields=["unit_price"],
        claims=[
            Claim(
                field="unit_price",
                value=85.0,
                source_file=source_file,
                source_page=1,
                source_excerpt="Standard Unit Price: 85.00 INR per bottle",
                status="conflicting",
                notes="Standard pricing baseline",
                is_verified_fact=False
            ),
            Claim(
                field="unit_price",
                value=95.0,
                source_file=source_file,
                source_page=1,
                source_excerpt="Urgent Dispatch Unit Price: 95.00 INR per bottle (contradictory rush pricing stated)",
                status="conflicting",
                notes="Alternative rush pricing conflicts with standard rate",
                is_verified_fact=False
            ),
            Claim(
                field="moq",
                value=50,
                source_file=source_file,
                source_page=1,
                source_excerpt="Minimum Order Quantity (MOQ): 50 units",
                status="extracted",
                is_verified_fact=False
            ),
            Claim(
                field="capacity",
                value=400,
                source_file=source_file,
                source_page=1,
                source_excerpt="Maximum Production Capacity: 400 units",
                status="extracted",
                is_verified_fact=False
            ),
            Claim(
                field="delivery_days",
                value=3,
                source_file=source_file,
                source_page=1,
                source_excerpt="Delivery Lead Time: 3 business days",
                status="extracted",
                is_verified_fact=False
            )
        ],
        metadata={
            "extraction_engine": "MOCK_FALLBACK (Synthetic Demonstration Data)",
            "is_synthetic": True,
            "demo_scenario": "Conflicting unit prices between standard and rush quotes"
        }
    )


def mock_extract_supplier_data(
    document_text: str,
    source_file: str,
    source_pages: Optional[Union[int, Any]] = None
) -> SupplierQuotation:
    """Deterministic mock extraction fallback when Ollama is unavailable or mock mode is requested."""
    text_lower = (document_text or "").lower()
    
    if "gamma" in text_lower or "greensource" in text_lower or "sup-003" in text_lower:
        return create_mock_supplier_gamma(source_file)
    elif "beta" in text_lower or "bluewave" in text_lower or "sup-002" in text_lower:
        return create_mock_supplier_beta(source_file)
    elif "alpha" in text_lower or "apex" in text_lower or "sup-001" in text_lower:
        return create_mock_supplier_alpha(source_file)
    
    # For custom documents, run rule-based heuristic extraction so real document
    # excerpts, line contents, and page numbers are preserved.
    from procurax.extraction.validator import heuristic_extract_supplier_data
    heuristic_res = heuristic_extract_supplier_data(
        document_text=document_text,
        source_file=source_file,
        source_pages=source_pages,
        engine_label="MOCK_FALLBACK (Heuristic Parser)"
    )
    if heuristic_res.claims:
        return heuristic_res

    # Default fallback to clean Alpha profile
    return create_mock_supplier_alpha(source_file)
