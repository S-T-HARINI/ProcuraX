"""ProcuraX Demo Extraction Script.

Demonstrates end-to-end supplier information extraction grounded in source evidence.
Uses a clearly labeled synthetic supplier quotation.
"""

import json
from procurax.extraction import extract_supplier_data

# Clearly labeled synthetic demonstration quotation
DEMO_SYNTHETIC_QUOTATION = """--- Page 1 ---
[DEMO QUOTATION - SYNTHETIC DATA]
Quotation Reference: DEMO-SYNTH-2026-01
Supplier Name: Apex Sustainable Packaging Ltd.
Supplier ID: SUP-001
Date: March 15, 2026

Product: Reusable Industrial Bottle (500ml)
Pricing & Commercial Terms:
- Base Unit Price: 80.00 INR per bottle
- Minimum Order Quantity (MOQ): 100 units
- Monthly Production Capacity: 600 units
- Delivery Lead Time: 5 business days to regional hub
- Fixed Transportation Charge: 500.00 INR flat rate

Volume Incentive:
- 5% discount on bulk orders exceeding 500 units.

Sustainability Certifications:
- Certified 100% Ocean Bound Recycled HDPE
- Closed-loop zero-waste manufacturing guarantee
"""


def run_demo():
    print("=" * 70)
    print("PROCURAX: EVIDENCE-DRIVEN PROCUREMENT INTELLIGENCE DEMO")
    print("=" * 70)
    print("\n1. INPUT SUPPLIER DOCUMENT (SYNTHETIC DEMO DATA):")
    print("-" * 50)
    print(DEMO_SYNTHETIC_QUOTATION.strip())
    print("-" * 50)

    print("\n2. RUNNING SUPPLIER EXTRACTION...")
    # Extracts structured data grounded in source evidence (using mock fallback for instant deterministic demo)
    result = extract_supplier_data(
        document_text=DEMO_SYNTHETIC_QUOTATION,
        source_file="demo_quotation_apex.pdf",
        source_pages=1,
        use_mock=True
    )

    print("\n3. STRUCTURED PROCURAX SUPPLIER JSON OUTPUT:")
    print("-" * 50)
    print(json.dumps(result, indent=2))
    print("-" * 50)

    print("\n4. EVIDENCE GROUNDING SUMMARY:")
    print(f"Supplier:       {result['supplier_name']} ({result['supplier_id']})")
    print(f"Product:        {result['product_name']}")
    print(f"Unit Price:     {result['unit_price']} {result['currency']}")
    print(f"MOQ / Capacity: {result['moq']} / {result['capacity']} units")
    print(f"Delivery:       {result['delivery_days']} days | Freight: {result['transport_cost']} {result['currency']}")
    print(f"Missing Fields: {result['missing_fields'] or 'None (Complete quote)'}")
    print(f"Conflicting:    {result['conflicting_fields'] or 'None (Consistent)'}")
    print("\nExtracted Claims & Source Grounding:")
    for idx, claim in enumerate(result["claims"], 1):
        print(f"  [{idx}] {claim['field']}: {claim['value']}")
        print(f"      Source File:   {claim['source_file']} (Page {claim['source_page']})")
        print(f"      Source Excerpt: \"{claim['source_excerpt']}\"")
        print(f"      Status:        {claim['status']} (Verified Fact: {claim.get('is_verified_fact', False)})")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
