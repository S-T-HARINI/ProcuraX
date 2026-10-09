# ProcuraX — Procurement Optimization, Scenarios, and Graph Engine

**Branch:** `feature/optimization-graph` (Person 3)  
**Role:** Landed-Cost Calculation, Supplier Allocation Optimizer, Scenario Simulations, and Evidence-to-Decision Consistency Graph.

---

## 1. Overview & Architectural Guarantees

All modules are designed to run **purely on CPU**, deterministically, without requiring Gemma 4 or a GPU. All algorithms use exact mathematical formulations and standard data structures (`scipy.optimize.milp`, `networkx`, `pydantic`).

Key Principles:
- **Shared JSON Contract Compliance:** Uses the shared supplier schema from the Universal Project Prompt.
- **Honest Null Handling:** Unknown numeric values are preserved as `null`, never replaced with zero.
- **Currency Isolation:** Currency codes are strictly preserved; multi-currency conversions are disallowed unless explicit exchange rates are provided.
- **Evidence-to-Decision Integrity:** Claims are explicitly marked `is_verified: False` (never assumed as ground-truth facts). Sourcing recommendations automatically flag `DEPENDS_ON_INCOMPLETE_DATA` if any allocated supplier has missing attributes.

---

## 2. Windows PowerShell Setup & Execution

### Prerequisites
- Python 3.10+ (tested on Python 3.13.5)

### Installation
```powershell
# From the repository root (d:\ProcuraX-team)
pip install -r requirements.txt
```

### Run All Unit Tests
```powershell
python -m pytest -v tests/
```

### Run End-to-End Demonstration
```powershell
python demo.py
```

---

## 3. Interfaces & Contracts for Person 2 (Backend Integration)

Person 2 can directly import from `procurax`:
```python
from procurax import (
    calculate_landed_cost,
    optimize_allocation,
    simulate_scenario,
    build_procurement_graph,
    Supplier,
    CostBreakdown,
    OptimizationSummary,
    ScenarioImpact,
)
```

### Task 1: Landed-Cost Calculation
```python
def calculate_landed_cost(
    supplier: Union[Dict[str, Any], Supplier],
    quantity: int,
    additional_charges: float = 0.0,
    discount_pct: float = 0.0,
    target_currency: Optional[str] = None,
    currency_rates: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
```
**Output JSON Contract:**
```json
{
  "supplier_id": "SUP-001",
  "supplier_name": "EcoPak",
  "quantity": 200,
  "unit_price": 80.0,
  "base_cost": 16000.0,
  "transport_cost": 500.0,
  "additional_charges": 0.0,
  "discounts": 0.0,
  "total_landed_cost": 16500.0,
  "cost_per_unit": 82.5,
  "currency": "INR",
  "missing_cost_inputs": [],
  "is_complete": true,
  "warnings": []
}
```

### Task 2: Supplier Allocation Optimizer
```python
def optimize_allocation(
    suppliers: List[Union[Dict[str, Any], Supplier]],
    demand: int,
    budget: Optional[float] = None,
    allow_overdelivery: bool = False,
    base_currency: Optional[str] = None,
    currency_rates: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
```
**Output JSON Contract:**
```json
{
  "status": "optimal",
  "is_feasible": true,
  "requested_demand": 500,
  "allocated_demand": 500,
  "unmet_demand": 0,
  "total_cost": 37950.0,
  "currency": "INR",
  "budget": 45000.0,
  "budget_utilized_pct": 84.33,
  "explanations": [
    "Optimal allocation found meeting 500/500 units across 2 supplier(s) for a total cost of 37,950.00 INR."
  ],
  "allocations": [
    {
      "supplier_id": "SUP-002",
      "supplier_name": "PrimeHoldings Corp",
      "allocated_quantity": 300,
      "cost_breakdown": { ... },
      "capacity": 300,
      "moq": 150,
      "share_of_demand_pct": 60.0
    }
  ],
  "unassigned_suppliers": ["SUP-001"],
  "warnings": []
}
```

### Task 3: Scenario Simulations
```python
def simulate_scenario(
    suppliers: List[Union[Dict[str, Any], Supplier]],
    demand: int,
    scenario: Dict[str, Any],
    budget: Optional[float] = None,
    currency_rates: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
```
**Scenario Definition Types:**
- Price Shock: `{"type": "price_increase", "supplier_id": "SUP-002", "percentage": 25.0}`
- Capacity Disruption: `{"type": "capacity_reduction", "supplier_id": "SUP-001", "percentage": 50.0}`
- Compound Disruption: `{"type": "compound", "scenarios": [...]}`

**Output JSON Contract:**
```json
{
  "scenario_type": "price_increase",
  "parameters": { ... },
  "baseline_status": "optimal",
  "scenario_status": "optimal",
  "is_feasible": true,
  "total_cost_delta": 1300.0,
  "percentage_cost_change": 3.43,
  "quantity_changes": {
    "SUP-001": 100,
    "SUP-002": -300,
    "SUP-003": 200
  },
  "narrative_explanation": "Scenario Applied: Increased unit price for SUP-002... Cost increased by 1,300.00...",
  "baseline_summary": { ... },
  "scenario_summary": { ... }
}
```

### Task 4: Evidence-to-Decision Consistency Graph
```python
def build_procurement_graph(
    suppliers: List[Union[Dict[str, Any], Supplier]],
    allocation: Dict[str, Any],
    risks: Optional[List[Dict[str, Any]]] = None,
    conflicts: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
```
**Output JSON Contract (Directly pluggable into React Flow / Cytoscape / D3):**
```json
{
  "nodes": [
    {
      "id": "supplier:SUP-001",
      "type": "supplier",
      "label": "Supplier: EcoPak (SUP-001)",
      "supplier_id": "SUP-001"
    },
    {
      "id": "claim:SUP-001:unit_price:0",
      "type": "claim",
      "label": "Claim: unit_price = 80.0",
      "field": "unit_price",
      "value": "80.0",
      "status": "extracted",
      "is_verified": false
    },
    {
      "id": "evidence:SUP-001:unit_price:0",
      "type": "evidence",
      "label": "Evidence: p.1",
      "source_file": "quotation_ecopak.pdf",
      "page": 1,
      "excerpt": "Quoted unit price INR 80.00..."
    },
    {
      "id": "missing:SUP-003:delivery_days",
      "type": "missing_info",
      "label": "Missing: delivery_days (SUP-003)",
      "field": "delivery_days",
      "severity": "medium"
    },
    {
      "id": "decision:recommendation",
      "type": "recommendation",
      "label": "Sourcing Recommendation",
      "status": "optimal",
      "is_feasible": true
    }
  ],
  "edges": [
    {
      "source": "claim:SUP-001:unit_price:0",
      "target": "evidence:SUP-001:unit_price:0",
      "type": "SUPPORTED_BY",
      "label": "supported by excerpt"
    },
    {
      "source": "decision:recommendation",
      "target": "missing:SUP-003:delivery_days",
      "type": "DEPENDS_ON_INCOMPLETE_DATA",
      "label": "CAUTION: relies on missing data"
    }
  ],
  "graph_metrics": {
    "node_count": 22,
    "edge_count": 26,
    "is_dag": true,
    "node_types": ["document", "supplier", "claim", "evidence", "missing_info", "cost_calculation", "supplier_risk", "allocation", "recommendation"],
    "edge_types": ["CLAIMS", "EXTRACTED_FROM", "SUPPORTED_BY", "HAS_MISSING_INFO", "INFLUENCES_COST", "EVALUATES_COST", "EXPOSES_RISK", "DETERMINES_ALLOCATION", "AFFECTS_ALLOCATION", "CONTRIBUTES_TO", "DEPENDS_ON_INCOMPLETE_DATA"]
  },
  "decision_audit": {
    "status": "optimal",
    "is_feasible": true,
    "depends_on_incomplete_data": true,
    "affected_suppliers": ["SUP-003"],
    "unverified_claims_count": 4,
    "documents_referenced": ["quotation_ecopak.pdf", "prime_rate_card.xlsx", "aeroplastic_quote.pdf"],
    "total_nodes": 22,
    "total_edges": 26
  }
}
```

---

## 4. Test Verification
All 19 tests in `tests/` pass with 100% success rate:
- `tests/test_cost.py`: 5 passed
- `tests/test_optimizer.py`: 6 passed
- `tests/test_scenarios.py`: 4 passed
- `tests/test_graph.py`: 4 passed
