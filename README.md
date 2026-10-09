# ProcuraX — FastAPI Backend & Integration

ProcuraX is an Evidence-Driven Procurement Intelligence and Sourcing Optimization platform. This backend API connects document parsing, Gemma 4 claim extraction, landed-cost optimization, price/capacity scenario simulation, and evidence-to-decision consistency graphs.

---

## 🚀 Quickstart (Windows PowerShell Instructions)

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
Open interactive Swagger API Docs at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 4. Run Test Suite
```powershell
pytest tests/ -v
```

---

## 📡 API Endpoints Summary

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health check |
| `POST` | `/api/documents/upload` | Upload & parse supplier PDF/CSV/XLSX files with page references |
| `POST` | `/api/extract` | Extract structured claims from quotation text |
| `POST | `/api/optimize` | Optimize procurement allocation under MOQ, capacity, budget, and scenario constraints |
| `POST` | `/api/graph` | Generate Evidence-to-Decision Consistency Graph (Nodes & Edges) |

---

## 🤝 Teammate Integration Interfaces

### Person 1 — Gemma 4 Extraction (`feature/gemma-extraction`)
Person 1 can plug their Gemma model by inheriting from `BaseExtractionService` in `backend/app/services/extraction_service.py`:

```python
from backend.app.models import ExtractRequest, ExtractResponse, SupplierQuote

class GemmaExtractionService:
    def extract(self, request: ExtractRequest) -> ExtractResponse:
        # 1. Call Gemma 4 E2B inference endpoint / local model runner
        # 2. Extract structured SupplierQuote objects preserving source file/page citations
        # 3. Return ExtractResponse with is_mock=False
        pass
```

### Person 3 — Optimization & Graph (`feature/optimization-graph`)
Person 3 can plug their optimization and graph modules into `backend/app/services/`:

- **Optimization**: Implement `BaseOptimizationService` in `backend/app/services/optimization_service.py`:
```python
from backend.app.models import OptimizationRequest, OptimizationResponse

class PuLPOptimizationService:
    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        # Linear programming optimization solver (PuLP / SciPy)
        pass
```

- **Graph**: Implement `BaseGraphService` in `backend/app/services/graph_service.py`:
```python
from backend.app.models import GraphRequest, GraphResponse

class EvidenceGraphService:
    def build_graph(self, request: GraphRequest) -> GraphResponse:
        # Dynamic network construction connecting document -> claim -> supplier -> decision
        pass
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
*Rules: Unknown numeric values must be `null` (never `0`). Currencies must not be converted without explicit rates.*
