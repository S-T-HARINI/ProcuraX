"""Tests for ProcuraX supplier quotation extraction module.

Covers:
- Shared supplier JSON schema compliance
- Null for unknown numbers (never zero)
- Excerpt preservation and page attribution
- Conflict, ambiguity, and missing fields detection
- Mock fallback determinism
- Full end-to-end extraction with Gemma 4 E2B
"""

import json
import unittest

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
from procurax.extraction.schema import SupplierQuotation
from procurax.extraction.validator import (
    detect_page_number,
    verify_and_reconcile_quotation,
)


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


class TestMockExtractionFallback(unittest.TestCase):
    """Test deterministic mock extraction fallback."""

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


class TestGemma4ExtractionIntegration(unittest.TestCase):
    """End-to-end integration test of Gemma 4 E2B extraction via Ollama."""

    def test_live_gemma4_extraction_synthetic_doc(self):
        """Test full extraction of a synthetic quotation using Gemma 4 E2B."""
        synthetic_quotation = """--- Page 1 ---
[DEMO QUOTATION - SYNTHETIC DATA]
Supplier: GreenPlanet Containers
Supplier ID: SUP-LIVE-001
Item: Reusable Industrial Bottle
Unit Price: 80.00 INR per unit
Minimum Order Quantity: 100 units
Monthly Supply Capacity: 600 units
Delivery Lead Time: 5 business days
Transportation Cost: 500.00 INR flat rate
Sustainability: 100% Recycled Post-Consumer PET
"""
        result = extract_supplier_data(
            document_text=synthetic_quotation,
            source_file="synthetic_greenplanet_quote.txt",
            source_pages=1,
            use_mock=False,
            model="gemma4:e2b",
            allow_fallback=False
        )

        # Validate essential contract keys exist
        required_keys = [
            "supplier_id", "supplier_name", "product_name",
            "unit_price", "currency", "moq", "capacity",
            "delivery_days", "transport_cost", "sustainability_claims",
            "missing_fields", "claims"
        ]
        for key in required_keys:
            self.assertIn(key, result, f"Missing required contract key: {key}")

        # Check values
        self.assertEqual(result["currency"], "INR")
        self.assertAlmostEqual(float(result["unit_price"]), 80.0, places=1)
        self.assertEqual(int(result["moq"]), 100)
        self.assertEqual(int(result["capacity"]), 600)
        self.assertEqual(int(result["delivery_days"]), 5)
        self.assertAlmostEqual(float(result["transport_cost"]), 500.0, places=1)

        # Check evidence claims
        self.assertGreater(len(result["claims"]), 0)
        for claim in result["claims"]:
            self.assertIn("field", claim)
            self.assertIn("value", claim)
            self.assertIn("source_file", claim)
            self.assertEqual(claim["source_file"], "synthetic_greenplanet_quote.txt")
            self.assertIn("source_excerpt", claim)
            self.assertTrue(len(claim["source_excerpt"]) > 0)
            self.assertFalse(claim.get("is_verified_fact", True))

        # Check valid JSON serializability
        serialized = json.dumps(result, indent=2)
        self.assertTrue(len(serialized) > 0)


if __name__ == "__main__":
    unittest.main()
