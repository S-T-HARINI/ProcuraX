# ProcuraX — FastAPI Backend & Integration

ProcuraX is an Evidence-Driven Procurement Intelligence and Sourcing Optimization platform powered by Gemma 4. This FastAPI backend coordinates document processing (PDF, CSV, XLSX), supplier claim extraction, landed-cost optimization, scenario simulations, and evidence-to-decision graph construction.

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

### 3. Start Development Server
```powershell
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```
Interactive OpenAPI Documentation is available at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 4. Run Test Suite
```powershell
pytest tests/ -v
```

---

## 📡 API Endpoints Overview

| Method | Endpoint | Description | Status Codes |
|---|---|---|---|
| `GET` | `/api/health` | System health & version check | `200` |
| `POST` | `/api/documents/upload` | Upload & parse supplier PDF/CSV/XLSX quotations with page citations | `200`, `400`, `500` |
| `POST` | `/api/extract` | Extract structured supplier information & source-linked claims | `200`, `422`, `500` |
| `POST` | `/api/optimize` | Sourcing allocation optimization under demand, MOQ, capacity & scenarios | `200`, `400`, `422`, `500` |
| `POST` | `/api/graph` | Construct Evidence-to-Decision Consistency Graph (Nodes & Edges) | `200`, `400`, `422`, `500` |

---

## 🤝 Teammate Integration Interfaces

### Person 1 — Gemma 4 Extraction (`feature/gemma-extraction`)
Implement `BaseExtractionService` in `backend/app/services/extraction_service.py` or specify environment variable `GEMMA_API_URL`:

```python
from backend.app.models import ExtractRequest, ExtractResponse

class BaseExtractionService(Protocol):
    def extract(self, request: ExtractRequest) -> ExtractResponse:
        ...
```

### Person 3 — Optimization & Graph (`feature/optimization-graph`)
- **Optimization**: Implement `BaseOptimizationService` in `backend/app/services/optimization_service.py`:
```python
from backend.app.models import OptimizationRequest, OptimizationResponse

class BaseOptimizationService(Protocol):
    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        ...
```

- **Graph**: Implement `BaseGraphService` in `backend/app/services/graph_service.py`:
```python
from backend.app.models import GraphRequest, GraphResponse

class BaseGraphService(Protocol):
    def build_graph(self, request: GraphRequest) -> GraphResponse:
        ...
```

---

## 🔒 Shared Supplier JSON Contract

```json
{
  "supplier_id": "SUP-001",
  "supplier_name": "Apex Eco Solutions",
  "product_name": "Reusable Bottle",
  "unit_price": 80.0,
  "currency": "INR",
  "moq": 100,
  "capacity": 600,
  "delivery_days": 5,
  "transport_cost": 500.0,
  "sustainability_claims": ["100% Recyclable Packaging"],
  "missing_fields": [],
  "claims": [
    {
      "field": "unit_price",
      "value": 80.0,
      "source_file": "supplier_a.pdf",
      "source_page": 1,
      "source_excerpt": "Unit price quoted at INR 80.",
      "status": "extracted"
    }
  ]
}
```
*Note: Unknown numeric values must remain `null` (`None`). Never use `0` as a default substitute for unknown data.*
