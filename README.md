# ProcuraX — End-to-End Procurement Intelligence Backend

ProcuraX is an Evidence-Driven Procurement Intelligence and Sourcing Optimization platform powered by Gemma 4. This FastAPI backend integrates document processing, Gemma 4 claim extraction, MILP landed-cost optimization, price/capacity scenario simulation, and evidence-to-decision consistency graph construction into a unified end-to-end workflow.

---

## 🚀 Quickstart Instructions (Windows PowerShell)

### 1. Create and Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Run FastAPI Development Server
```powershell
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```
Interactive Swagger API Docs are available at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 4. Run Complete Test Suite (19 Tests)
```powershell
pytest tests/ -v
```

---

## 📡 API Endpoints Summary

| Method | Endpoint | Description | Status Codes |
|---|---|---|---|
| `GET` | `/api/health` | Service health & version check | `200` |
| `POST` | `/api/documents/upload` | Upload & parse supplier PDF/CSV/XLSX quotation with page citations | `200`, `400`, `500` |
| `POST` | `/api/extract` | Extract structured supplier quotation & claims grounded in source evidence | `200`, `422`, `500` |
| `POST` | `/api/optimize` | Landed cost & MILP sourcing allocation optimizer with scenario simulations | `200`, `400`, `422`, `500` |
| `POST` | `/api/graph` | Construct Evidence-to-Decision Consistency Graph (Nodes & Edges) | `200`, `400`, `422`, `500` |
| `POST` | `/api/workflow` | **End-to-End Sourcing Workflow**: Upload -> Extract -> Validate -> Optimize -> Graph | `200`, `400`, `422`, `500` |

---

## 🔄 End-to-End Demo Workflow (`POST /api/workflow`)

Send a single request to run the complete end-to-end procurement intelligence pipeline:

### Example Request
```json
{
  "document_filename": "supplier_quotation_alpha.pdf",
  "document_text": "Supplier: Apex Sustainable Packaging Ltd.\nSupplier ID: SUP-001\nBase Unit Price: 80.00 INR per bottle\nMinimum Order Quantity (MOQ): 100 units\nProduction Monthly Capacity: 600 units\nStandard Delivery Lead Time: 5 business days\nTransportation & Freight: 500.00 INR flat charge\nSustainability: Certified 100% Ocean Bound Recycled HDPE",
  "target_demand": 500,
  "budget_limit": 50000.0,
  "scenario": {
    "type": "price_increase",
    "supplier_id": "SUP-001",
    "percentage": 10.0
  },
  "use_mock_extraction": false
}
```

### Example Response Structure
```json
{
  "document": {
    "filename": "supplier_quotation_alpha.pdf",
    "raw_text": "Supplier: Apex Sustainable Packaging Ltd...."
  },
  "extraction": {
    "suppliers": [
      {
        "supplier_id": "SUP-001",
        "supplier_name": "Apex Sustainable Packaging Ltd.",
        "product_name": "Reusable Industrial Bottle (500ml)",
        "unit_price": 80.0,
        "currency": "INR",
        "moq": 100,
        "capacity": 600,
        "claims": [...]
      }
    ],
    "is_mock": true
  },
  "optimization": {
    "status": "optimal",
    "is_feasible": true,
    "target_demand": 500,
    "total_allocated_quantity": 500,
    "total_landed_cost": 44500.0,
    "allocations": [...],
    "scenario_impact": {...}
  },
  "graph": {
    "nodes": [
      {"id": "supplier:SUP-001", "type": "supplier", "label": "Supplier: Apex Sustainable Packaging Ltd."},
      {"id": "claim:SUP-001:unit_price:0", "type": "claim", "label": "Claim: unit_price = 80.0"},
      {"id": "decision:recommendation", "type": "recommendation", "label": "Sourcing Recommendation"}
    ],
    "edges": [...]
  },
  "summary": "ProcuraX Sourcing Report for 'supplier_quotation_alpha.pdf':\n• Extracted claims for 1 supplier(s)...\n• Target Demand: 500 units. Status: OPTIMAL.\n• Total Landed Cost: 44,500.00 INR.\n• Evidence Graph: 8 nodes and 10 edges created linking source claims to allocation decisions."
}
```

---

## 🛠️ Troubleshooting & Module Fallback Rules

1. **Ollama / Gemma 4 Unavailable**:
   - The backend detects when Ollama is offline or uninstalled and triggers a fail-safe fallback (`is_mock=True`).
   - Responses set `metadata.fallback_triggered = True` so frontend clients can distinguish real Gemma extractions from fallback data.

2. **File Parsing Errors**:
   - Uploading corrupted PDFs or unsupported formats returns a `400 Bad Request` with exact diagnostic messages.

3. **Infeasible Optimization Demands**:
   - If target demand exceeds total supplier capacity or budget is exceeded, the optimizer returns `status: "infeasible"` with detailed explanation strings in `explanations` list.

---

## 🔒 Shared Supplier JSON Contract

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
  "sustainability_claims": ["Certified 100% Ocean Bound Recycled HDPE"],
  "missing_fields": [],
  "claims": [
    {
      "field": "unit_price",
      "value": 80.0,
      "source_file": "supplier_a.pdf",
      "source_page": 1,
      "source_excerpt": "Base Unit Price: 80.00 INR per bottle",
      "status": "extracted"
    }
  ]
}
```
*Note: Unknown numeric values must remain `null` (`None`). Never use `0` as a default substitute for unknown data.*
