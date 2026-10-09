"""Tests for ProcuraX supplier quotation extraction module.

Covers:
- Shared supplier JSON schema compliance
- Null for unknown numbers (never zero)
- Excerpt preservation and page attribution
- Conflict, ambiguity, and missing fields detection
- Mock fallback and heuristic parser determinism
- Full extraction on sample supplier documents without requiring a live Ollama model
- Optional live Ollama integration test (skipped when offline)
"""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from procurax.extraction.extractor import (
    extract_supplier_data,
    extract_supplier_data_model,
)
from procurax.extraction.mock_data import (
    SYNTHETIC_DOC_ALPHA,
    SYNTHETIC_DOC_BETA,
    SYNTHETIC_DOC_GAMMA,
    mock_extract_supplier_data,
)
from procurax.extraction.schema import Claim, SupplierQuotation
from procurax.extraction.validator import (
    detect_page_number,
    extract_json_from_text,
    heuristic_extract_supplier_data,
    verify_and_reconcile_quotation,
)


# Sample supplier quotation documents for testing
SAMPLE_COMPLETE_DOC = """--- Page 1 ---
QUOTATION: QUOTE-2026-COMPLETE
Supplier: Apex Sustainable Packaging Ltd.
Supplier ID: SUP-001
Date: March 15, 2026

Product: Reusable Industrial Bottle (500ml)
Pricing & Terms:
- Unit Price: 80.00 INR per bottle
- Minimum Order Quantity (MOQ): 100 units
- Monthly Production Capacity: 600 units
- Delivery Lead Time: 5 business days
- Transportation Cost: 500.00 INR flat rate

Sustainability:
- 100% Ocean Bound Recycled HDPE
- Closed-loop manufacturing
"""

SAMPLE_MISSING_FIELDS_DOC = """--- Page 1 ---
QUOTATION: QUOTE-2026-MISSING
Supplier: BlueWave Logistics & Supplies
Supplier ID: SUP-002
Date: March 16, 2026

Item: Reusable Industrial Bottle (500ml)
Pricing:
- Base Unit Price: 72.50 INR per unit
- Minimum Order Quantity: 300 units
- Monthly Capacity: 1000 units
- Delivery Lead Time: Not specified in this quotation
- Freight Cost: Shipping charges to be determined later upon delivery
"""

SAMPLE_CONFLICTING_DOC = """--- Page 1 ---
QUOTATION: QUOTE-2026-CONFLICT
Supplier: GreenSource Manufacturing Co.
Supplier ID: SUP-003
Date: March 17, 2026

Product: Reusable Industrial Bottle (500ml)
Pricing:
- Standard Unit Price: 85.00 INR per bottle
- Rush Order Unit Price: 95.00 INR per bottle (Urgent dispatch rate)
- MOQ: 50 units
- Monthly Capacity: 400 units
- Delivery: 3 business days
- Transportation: 350.00 INR
"""

SAMPLE_AMBIGUOUS_DOC = """--- Page 1 ---
QUOTATION: QUOTE-2026-AMBIGUOUS
Supplier: Variable Logistics Co.
Supplier ID: SUP-004

Item: Reusable Industrial Bottle
Unit Price: 75.00 INR
MOQ: 150 units
Capacity: 800 units
Delivery Lead Time: 5 to 14 business days (variable backlog)
Freight: TBD destination pending
"""


class TestProcuraXSchemaAndValidator(unittest.TestCase):
    """Test schema adherence and post-processing validation rules."""

    def test_null_for_unknown_numeric_values(self):
        """Verify that unknown numeric fields are None/null, never 0."""
        raw_data = {
            "supplier_id": "SUP-TEST",
            "supplier_name": "Test Supplier",
            "unit_price": None,
            "currency": "INR",
            "moq": None,
            "capacity": None,
            "delivery_days": None,
            "transport_cost": None,
            "claims": []
        }
        quotation = verify_and_reconcile_quotation(
            raw_data=raw_data,
            document_text="Supplier Quote without pricing",
            source_file="test_doc.pdf"
        )
        data = quotation.to_contract_dict()
        self.assertIsNone(data["unit_price"])
        self.assertIsNone(data["moq"])
        self.assertIsNone(data["capacity"])
        self.assertIsNone(data["delivery_days"])
        self.assertIsNone(data["transport_cost"])
        self.assertIn("unit_price", data["missing_fields"])
        self.assertIn("moq", data["missing_fields"])

    def test_zero_not_substituted_for_unknown(self):
        """Verify that a zero is discarded unless explicit free keywords are in document."""
        raw_data = {
            "supplier_id": "SUP-TEST",
            "transport_cost": 0.0,
            "claims": []
        }
        # Document does NOT say free shipping
        quotation = verify_and_reconcile_quotation(
            raw_data=raw_data,
            document_text="Standard quote with unmentioned shipping",
            source_file="test_doc.pdf"
        )
        self.assertIsNone(quotation.transport_cost)

        # Document explicitly says Free Delivery
        quotation_free = verify_and_reconcile_quotation(
            raw_data={"transport_cost": 0.0, "claims": []},
            document_text="Includes Free Delivery to site",
            source_file="test_doc.pdf"
        )
        self.assertEqual(quotation_free.transport_cost, 0.0)

    def test_conflicting_claims_detection(self):
        """Verify that multiple conflicting claims for a field are detected."""
        raw_data = {
            "supplier_id": "SUP-CONF",
            "unit_price": 85.0,
            "claims": [
                {
                    "field": "unit_price",
                    "value": 85.0,
                    "source_excerpt": "Standard rate 85.00 INR",
                    "status": "extracted"
                },
                {
                    "field": "unit_price",
                    "value": 95.0,
                    "source_excerpt": "Rush rate 95.00 INR",
                    "status": "extracted"
                }
            ]
        }
        quotation = verify_and_reconcile_quotation(
            raw_data=raw_data,
            document_text="Standard rate 85.00 INR. Rush rate 95.00 INR.",
            source_file="conflict_doc.pdf"
        )
        self.assertIn("unit_price", quotation.conflicting_fields)
        self.assertTrue(any(c.status == "conflicting" for c in quotation.claims))

    def test_claims_are_not_verified_facts(self):
        """Verify that extracted claims have is_verified_fact=False."""
        raw_data = {
            "supplier_id": "SUP-001",
            "claims": [
                {
                    "field": "capacity",
                    "value": 500,
                    "source_excerpt": "Capacity: 500 units",
                    "status": "extracted"
                }
            ]
        }
        quotation = verify_and_reconcile_quotation(
            raw_data=raw_data,
            document_text="Capacity: 500 units",
            source_file="doc.pdf"
        )
        self.assertFalse(quotation.claims[0].is_verified_fact)

    def test_page_number_detection(self):
        """Verify page number extraction from multi-page document text."""
        doc = "--- Page 1 ---\nSupplier Intro\n--- Page 2 ---\nBase Price: 80 INR"
        page = detect_page_number("Base Price: 80 INR", doc)
        self.assertEqual(page, 2)

    def test_trailing_comma_json_extraction(self):
        """Verify extract_json_from_text handles LLM outputs with trailing commas."""
        raw_llm_output = """Here is the result:
```json
{
  "supplier_id": "SUP-001",
  "unit_price": 80.0,
}
```
"""
        parsed = extract_json_from_text(raw_llm_output)
        self.assertEqual(parsed["supplier_id"], "SUP-001")
        self.assertEqual(parsed["unit_price"], 80.0)


class TestMockAndHeuristicExtractionOffline(unittest.TestCase):
    """Test deterministic mock extraction and heuristic fallback (requires no model)."""

    def test_mock_alpha_contract(self):
        """Verify Supplier Alpha mock produces valid ProcuraX contract JSON."""
        result = mock_extract_supplier_data(SYNTHETIC_DOC_ALPHA, "synthetic_alpha.pdf")
        contract = result.to_contract_dict()
        
        self.assertEqual(contract["supplier_id"], "SUP-001")
        self.assertEqual(contract["unit_price"], 80.0)
        self.assertEqual(contract["currency"], "INR")
        self.assertEqual(contract["moq"], 100)
        self.assertEqual(contract["capacity"], 600)
        self.assertEqual(contract["delivery_days"], 5)
        self.assertEqual(contract["transport_cost"], 500.0)
        self.assertTrue(contract["metadata"]["is_synthetic"])
        self.assertGreater(len(contract["claims"]), 0)

        # Ensure JSON serializable
        json_str = json.dumps(contract)
        self.assertIn('"supplier_id": "SUP-001"', json_str)

    def test_mock_beta_missing_and_ambiguous(self):
        """Verify Supplier Beta correctly flags missing and ambiguous fields."""
        result = mock_extract_supplier_data(SYNTHETIC_DOC_BETA, "synthetic_beta.pdf")
        contract = result.to_contract_dict()

        self.assertEqual(contract["supplier_id"], "SUP-002")
        self.assertIsNone(contract["delivery_days"])
        self.assertIsNone(contract["transport_cost"])
        self.assertIn("delivery_days", contract["missing_fields"])
        self.assertIn("transport_cost", contract["missing_fields"])
        self.assertIn("delivery_days", contract["ambiguous_fields"])

    def test_mock_gamma_conflicts(self):
        """Verify Supplier Gamma flags conflicting prices."""
        result = mock_extract_supplier_data(SYNTHETIC_DOC_GAMMA, "synthetic_gamma.pdf")
        contract = result.to_contract_dict()

        self.assertEqual(contract["supplier_id"], "SUP-003")
        self.assertIn("unit_price", contract["conflicting_fields"])
        self.assertTrue(any(c["status"] == "conflicting" for c in contract["claims"]))

    def test_heuristic_extraction_custom_document(self):
        """Verify heuristic extractor extracts real excerpts from an arbitrary custom document."""
        custom_doc = """--- Page 1 ---
Supplier Name: Delta Pack Ltd
Supplier ID: SUP-099
Item Name: Bio Straws
Base Price: 15.50 INR
MOQ: 1000
Monthly Capacity: 25000
Lead Time: 4
Freight Cost: 250.00 INR
Sustainability: 100% Home Compostable
"""
        quotation = heuristic_extract_supplier_data(custom_doc, "delta.pdf", source_pages=1)
        contract = quotation.to_contract_dict()
        
        self.assertEqual(contract["supplier_id"], "SUP-099")
        self.assertEqual(contract["unit_price"], 15.50)
        self.assertEqual(contract["currency"], "INR")
        self.assertEqual(contract["moq"], 1000)
        self.assertEqual(contract["capacity"], 25000)
        self.assertEqual(contract["delivery_days"], 4)
        self.assertEqual(contract["transport_cost"], 250.00)
        self.assertIn("Base Price: 15.50 INR", [c["source_excerpt"] for c in contract["claims"]])


class TestExtractionWithSampleDocumentsOffline(unittest.TestCase):
    """Test full extraction flow on sample documents without requiring a live Ollama model."""

    @patch("procurax.extraction.extractor.chat")
    def test_complete_quotation_extraction(self, mock_chat):
        """Test extraction on a complete quotation document."""
        mock_model_output = {
            "supplier_id": "SUP-001",
            "supplier_name": "Apex Sustainable Packaging Ltd.",
            "product_name": "Reusable Industrial Bottle (500ml)",
            "unit_price": 80.0,
            "currency": "INR",
            "moq": 100,
            "capacity": 600,
            "delivery_days": 5,
            "transport_cost": 500.0,
            "discount_terms": None,
            "sustainability_claims": ["100% Ocean Bound Recycled HDPE"],
            "missing_fields": [],
            "ambiguous_fields": [],
            "conflicting_fields": [],
            "claims": [
                {
                    "field": "unit_price",
                    "value": 80.0,
                    "source_excerpt": "Unit Price: 80.00 INR per bottle",
                    "status": "extracted"
                },
                {
                    "field": "moq",
                    "value": 100,
                    "source_excerpt": "Minimum Order Quantity (MOQ): 100 units",
                    "status": "extracted"
                },
                {
                    "field": "capacity",
                    "value": 600,
                    "source_excerpt": "Monthly Production Capacity: 600 units",
                    "status": "extracted"
                },
                {
                    "field": "delivery_days",
                    "value": 5,
                    "source_excerpt": "Delivery Lead Time: 5 business days",
                    "status": "extracted"
                },
                {
                    "field": "transport_cost",
                    "value": 500.0,
                    "source_excerpt": "Transportation Cost: 500.00 INR flat rate",
                    "status": "extracted"
                }
            ]
        }
        mock_response = MagicMock()
        mock_response.message.content = json.dumps(mock_model_output)
        mock_chat.return_value = mock_response

        result = extract_supplier_data(
            document_text=SAMPLE_COMPLETE_DOC,
            source_file="sample_complete.pdf",
            source_pages=1,
            use_mock=False
        )

        # Validate shared schema keys
        self.assertEqual(result["supplier_id"], "SUP-001")
        self.assertEqual(result["unit_price"], 80.0)
        self.assertEqual(result["currency"], "INR")
        self.assertEqual(result["moq"], 100)
        self.assertEqual(result["capacity"], 600)
        self.assertEqual(result["delivery_days"], 5)
        self.assertEqual(result["transport_cost"], 500.0)
        self.assertEqual(result["missing_fields"], [])
        self.assertGreater(len(result["claims"]), 0)

        # Verify claims are not verified facts
        for claim in result["claims"]:
            self.assertFalse(claim["is_verified_fact"])
            self.assertEqual(claim["source_file"], "sample_complete.pdf")

    @patch("procurax.extraction.extractor.chat")
    def test_missing_values_document(self, mock_chat):
        """Test extraction on document with missing lead time and freight cost."""
        mock_model_output = {
            "supplier_id": "SUP-002",
            "supplier_name": "BlueWave Logistics & Supplies",
            "product_name": "Reusable Industrial Bottle (500ml)",
            "unit_price": 72.50,
            "currency": "INR",
            "moq": 300,
            "capacity": 1000,
            "delivery_days": None,
            "transport_cost": None,
            "missing_fields": ["delivery_days", "transport_cost"],
            "claims": [
                {
                    "field": "unit_price",
                    "value": 72.50,
                    "source_excerpt": "Base Unit Price: 72.50 INR per unit",
                    "status": "extracted"
                }
            ]
        }
        mock_response = MagicMock()
        mock_response.message.content = json.dumps(mock_model_output)
        mock_chat.return_value = mock_response

        result = extract_supplier_data(
            document_text=SAMPLE_MISSING_FIELDS_DOC,
            source_file="sample_missing.pdf",
            source_pages=1,
            use_mock=False
        )

        self.assertIsNone(result["delivery_days"])
        self.assertIsNone(result["transport_cost"])
        self.assertIn("delivery_days", result["missing_fields"])
        self.assertIn("transport_cost", result["missing_fields"])

    @patch("procurax.extraction.extractor.chat")
    def test_conflicting_claims_document(self, mock_chat):
        """Test extraction on document with contradictory standard vs rush unit prices."""
        mock_model_output = {
            "supplier_id": "SUP-003",
            "supplier_name": "GreenSource Manufacturing Co.",
            "unit_price": 85.0,
            "currency": "INR",
            "conflicting_fields": ["unit_price"],
            "claims": [
                {
                    "field": "unit_price",
                    "value": 85.0,
                    "source_excerpt": "Standard Unit Price: 85.00 INR per bottle",
                    "status": "conflicting"
                },
                {
                    "field": "unit_price",
                    "value": 95.0,
                    "source_excerpt": "Rush Order Unit Price: 95.00 INR per bottle (Urgent dispatch rate)",
                    "status": "conflicting"
                }
            ]
        }
        mock_response = MagicMock()
        mock_response.message.content = json.dumps(mock_model_output)
        mock_chat.return_value = mock_response

        result = extract_supplier_data(
            document_text=SAMPLE_CONFLICTING_DOC,
            source_file="sample_conflict.pdf",
            source_pages=1,
            use_mock=False
        )

        self.assertIn("unit_price", result["conflicting_fields"])
        conflicting_claims = [c for c in result["claims"] if c["field"] == "unit_price"]
        self.assertGreaterEqual(len(conflicting_claims), 2)
        for c in conflicting_claims:
            self.assertEqual(c["status"], "conflicting")

    @patch("procurax.extraction.extractor.chat")
    def test_malformed_model_response_handles_gracefully(self, mock_chat):
        """Test that malformed JSON from the model triggers fallback without crashing."""
        mock_response = MagicMock()
        mock_response.message.content = "Malformed response with unclosed bracket: {\"supplier_name\": \"Broken\""
        mock_chat.return_value = mock_response

        # With allow_fallback=True, it should not raise an exception
        result = extract_supplier_data(
            document_text=SAMPLE_COMPLETE_DOC,
            source_file="sample_complete.pdf",
            allow_fallback=True
        )

        self.assertIsInstance(result, dict)
        self.assertIn("supplier_id", result)
        self.assertTrue(result["metadata"]["fallback_triggered"])


# Optional live integration test: only runs if explicitly requested via environment variable
@unittest.skipUnless(
    os.environ.get("PROCURAX_LIVE_TESTS") == "1",
    "Live Ollama tests skipped by default. Set PROCURAX_LIVE_TESTS=1 to run against local Ollama."
)
class TestGemma4LiveOllamaIntegration(unittest.TestCase):
    """Live Ollama integration test for local verification."""

    def test_live_gemma4_extraction(self):
        result = extract_supplier_data(
            document_text=SAMPLE_COMPLETE_DOC,
            source_file="sample_live.txt",
            source_pages=1,
            use_mock=False,
            model="gemma4:e2b",
            allow_fallback=False
        )
        self.assertEqual(result["currency"], "INR")
        self.assertAlmostEqual(float(result["unit_price"]), 80.0, places=1)


if __name__ == "__main__":
    unittest.main()
