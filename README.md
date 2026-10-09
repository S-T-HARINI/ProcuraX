# ProcuraX — Evidence-Driven Procurement Intelligence & Sourcing Optimization

ProcuraX is an AI-powered procurement intelligence platform powered by Gemma 4. It converts supplier quotation documents into structured claims, verifies evidence, calculates estimated landed costs, optimizes supplier allocations using MILP, simulates risk scenarios, and builds interactive evidence-to-decision lineage graphs.

---

## 🚀 Quickstart Instructions (Windows PowerShell)

### 1. Install Backend Dependencies
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Run Backend API Server
```powershell
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```
Interactive API Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 3. Run Frontend UI Application
```powershell
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000)

### 4. Run Test Suite
```powershell
pytest tests/ -v
```

---

## 🏗️ Integrated System Architecture

1. **Gemma 4 Claim Extraction (`procurax.extraction`)**: Extract structured supplier quotes with grounded citations from PDF/CSV/XLSX quotes using Gemma 4 via Ollama.
2. **Landed Cost & Optimization (`procurax.cost`, `procurax.optimizer`)**: Calculate landed costs and solve Mixed-Integer Linear Programs (MILP) under MOQ, capacity, and budget constraints.
3. **Scenario Simulator (`procurax.scenarios`)**: Simulate price hikes, capacity reductions, and transport disruptions.
4. **Evidence Lineage Graph (`procurax.graph`)**: NetworkX directed graph linking source documents, extracted claims, risks, and final sourcing recommendations.
5. **FastAPI Backend (`backend/app`)**: Unified REST API exposing health check, document upload, claim extraction, optimization, graph builder, and end-to-end workflow (`/api/workflow`).
6. **Next.js Frontend (`frontend/`)**: Professional dark-navy workspace UI with 7 hackathon pitch screens.
