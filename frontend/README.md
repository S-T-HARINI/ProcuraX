# ProcuraX — AI-Powered Procurement Intelligence Frontend

ProcuraX is an Evidence-Driven Procurement Intelligence and Sourcing Optimization platform built for hackathons and enterprise procurement teams.

This Next.js frontend delivers a modern UI with 7 interactive screens, realistic synthetic demo data, and a typed API client prepared for live integration with the FastAPI backend.

---

## 🚀 Quickstart Instructions (Windows PowerShell)

### 1. Install Frontend Dependencies
```powershell
cd D:\ProcuraX-frontend\frontend
npm install
```

### 2. Configure Environment (Optional)
Create `.env.local` if connecting to a custom backend host:
```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

### 3. Run Development Server
```powershell
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### 4. Production Build Verification
```powershell
npm run build
npm run start
```

---

## 📱 Integrated Frontend Screens

1. **Dashboard Overview**: Summary KPIs (Suppliers Analyzed, Optimal Landed Cost, Calculated Savings, Risk Alerts), Recharts supplier price benchmark chart, active risk warning cards.
2. **Quotation Upload**: Drag-and-drop file upload for PDF, CSV, and XLSX supplier quotes, simulated extraction progress, claim preview cards with missing field alerts.
3. **Supplier Comparison**: Interactive benchmark matrix with sorting (Unit Price, Capacity, MOQ), search filtering, and slide-over supplier detail inspection panel.
4. **Allocation Optimizer**: Target demand & max budget controls, MILP solver execution, allocated quantity tables, capacity utilization progress bars, cost breakdowns, and infeasibility alerts.
5. **Evidence Lineage Graph**: Interactive NetworkX/React Flow node map mapping source documents, extracted claims, landed cost calculations, supplier risks, and final sourcing recommendations.
6. **Scenario Simulator**: What-if risk simulator for price hikes (%), capacity cuts (%), and freight disruptions with baseline vs scenario spend comparison and narrative explanation.
7. **Evidence Audit Log**: Audit table for extracted claims showing filename, 1-indexed page citations, verbatim source excerpts, and claim status badges (`extracted`, `verified`, `conflicting`, `ambiguous`, `missing`).

---

## 🤝 Live Backend vs Demo Mode Rules

- **Demo Mode**: Enabled via the sidebar toggle or automatically triggered when the FastAPI backend is offline. Uses deterministic synthetic suppliers (`SUP-001`, `SUP-002`, `SUP-003`).
- **Live FastAPI Integration**: Connects to `http://127.0.0.1:8000` via `ApiClient.ts` for real Gemma 4 claim extractions (`/api/extract`), MILP solver optimizations (`/api/optimize`), lineage graph construction (`/api/graph`), and complete workflows (`/api/workflow`).
