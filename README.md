# ProcuraX: Evidence-Driven Procurement Intelligence

ProcuraX is an AI-powered procurement intelligence and sourcing optimization platform built for hackathons. It ingests supplier quotations, extracts structured supplier claims using **Gemma 4 E2B**, grounds every claim in verifiable source document excerpts, reconciles missing and conflicting information, and builds an **Evidence-to-Decision Consistency Graph**.

---

## 1. Gemma 4 Supplier Extraction Module (`feature/gemma-extraction`)

The extraction module converts unstructured or semi-structured quotation text (from PDFs, CSVs, or XLSX documents) into a validated, deterministic JSON structure matching the team's shared contract.

### Core Features

- **Local Inference via Ollama**: Connects to `gemma4:e2b` via Ollama's local chat endpoint using strict JSON mode.
- **Evidence Preservation**: Preserves source file name, page numbers, and verbatim textual excerpts for each extracted claim.
- **Distinction of Claims vs. Facts**: Every claim is explicitly tagged with `is_verified_fact: false`, preventing unverified supplier statements from being treated as established ground truth.
- **Deterministic Null Handling**: Unknown numeric values (price, MOQ, capacity, lead time, freight) are represented as `null`, never substituted with `0`.
- **Conflict & Ambiguity Detection**: Flags contradictory claims (e.g., standard price vs. rush price) into `conflicting_fields` and conditional statements (e.g., variable lead times or pending freight) into `ambiguous_fields`.
- **Deterministic Mock & Heuristic Fallbacks**: Fully testable offline without requiring a running Ollama model or GPU.

---

## 2. Shared Supplier JSON Contract

```json
{
  "supplier_id": "SUP-001",
  "supplier_name": "Apex Sustainable Packaging Ltd.",
  "product_name": "Reusable Industrial Bottle (500ml)",
  "unit_price": 80.0,
  "currency": "INR",
  "moq": 100,
  "capacity": 600,
  "delivery_days": 5,
  "transport_cost": 500.0,
  "discount_terms": "5% off on orders exceeding 500 units.",
  "sustainability_claims": [
    "Certified 100% Ocean Bound Recycled HDPE",
    "Closed-loop manufacturing process"
  ],
  "missing_fields": [],
  "ambiguous_fields": [],
  "conflicting_fields": [],
  "claims": [
    {
      "field": "unit_price",
      "value": 80.0,
      "source_file": "supplier_a.pdf",
      "source_page": 1,
      "source_excerpt": "Base Unit Price: 80.00 INR per bottle",
      "status": "extracted",
      "notes": null,
      "is_verified_fact": false
    }
  ],
  "metadata": {
    "extraction_engine": "Gemma 4 (gemma4:e2b)",
    "is_synthetic": false,
    "fallback_triggered": false
  }
}
```

---

## 3. Setup Instructions (Windows PowerShell)

### Prerequisites

1. **Python 3.12+**
2. **Ollama** installed with `gemma4:e2b` pulled:
   ```powershell
   ollama pull gemma4:e2b
   ```

### Virtual Environment Setup

```powershell
# Clone repository and switch to feature branch
git checkout feature/gemma-extraction

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

---

## 4. Usage Examples

### Basic Extraction

```python
from procurax.extraction import extract_supplier_data

quotation_text = """--- Page 1 ---
Supplier: Apex Sustainable Packaging Ltd.
Supplier ID: SUP-001
Item: Reusable Industrial Bottle (500ml)
Base Unit Price: 80.00 INR per bottle
Minimum Order Quantity (MOQ): 100 units
Monthly Capacity: 600 units
Delivery Lead Time: 5 business days
Transportation: 500.00 INR flat rate
Sustainability: 100% Ocean Bound Recycled HDPE
"""

# Extract supplier data grounded in source document
result = extract_supplier_data(
    document_text=quotation_text,
    source_file="supplier_quote.pdf",
    source_pages=1
)

print(result["supplier_name"])   # Apex Sustainable Packaging Ltd.
print(result["unit_price"])      # 80.0
print(result["claims"][0])       # Evidence claim with excerpt and source_file
```

### Offline / Mock Fallback Mode

For teammates (Backend API, Optimization) developing without a running Ollama model:

```python
from procurax.extraction import extract_supplier_data

# Immediate deterministic synthetic data for fast local testing
mock_result = extract_supplier_data(
    document_text="Supplier Beta",
    source_file="demo_beta.pdf",
    use_mock=True
)

print(mock_result["missing_fields"])  # ['delivery_days', 'transport_cost']
```

---

## 5. Testing Instructions

### Run Fast Offline Tests (Recommended)

Tests cover the schema validator, rule reconciler, mock fallbacks, and sample document extractions with mocked LLM responses. **Does not require a live Ollama daemon to run**:

```powershell
.\.venv\Scripts\python.exe -m unittest tests/test_extraction.py -v
```

### Run Live Model Integration Tests

To test end-to-end against the local Ollama `gemma4:e2b` model:

```powershell
$env:PROCURAX_LIVE_TESTS="1"
.\.venv\Scripts\python.exe -m unittest tests/test_extraction.py -v
```

---

## 6. Team Module Integration Notes

- **Person 1 (`feature/gemma-extraction`)**: Supplier quotation extraction, Gemma 4 E2B integration, and evidence tracking.
- **Person 2 (`feature/backend-api`)**: Connects `extract_supplier_data` to FastAPI upload endpoints (`POST /api/extract`).
- **Person 3 (`feature/optimization-graph`)**: Consumes the JSON output to build the Evidence-to-Decision Consistency Graph and run supplier allocation optimizations.
