# ProcuraX — Procurement Optimization, Scenarios, and Evidence Graph

**Branch:** `feature/optimization-graph` (Person 3)  
**Role:** Landed-Cost Calculation, Mixed-Integer Linear Programming (MILP) Allocation Optimizer, Scenario Simulation Engine, NetworkX Evidence-to-Decision Consistency Graph, and Backend Service Adapters.

---

## 1. Overview & Innovation Guarantees

All modules execute **purely on CPU**, deterministically, without requiring Gemma 4, GPU hardware, or external API keys.

### Architectural Principles
- **Shared JSON Contract Compliance:** Strictly adheres to the shared supplier interface schema from the Universal Project Prompt.
- **Honest Null Handling:** Missing numeric values are preserved as `null`. The system **never silently assumes unknown costs or values are zero**.
- **Transport Cost Assumptions:**
  - *Fixed Per Shipment (Default):* Logistics is charged as a flat freight fee per order/delivery batch (`transport_is_per_unit=False` or `transport_cost_type="fixed_per_shipment"`).
  - *Variable Per Unit:* Freight scales linearly with the quantity ordered (`transport_is_per_unit=True` or `transport_cost_type="per_unit"`).
  - Both conventions are fully supported in `calculate_landed_cost` and the MILP optimization solver.
- **Allocation & Exclusion Transparency:** Every evaluated supplier receives an explicit status (`allocated`, `unassigned`, or `excluded`) alongside detailed constraint notes or exclusion reasons (e.g. missing unit price, capacity < MOQ, non-competitive cost, or marked unavailable).
- **Infeasible Demand Reporting:** The optimizer explicitly reports infeasible demand (e.g. aggregate capacity shortfall, MOQ violations, budget deficits) and never claims demand was met when it was not.
- **Evidence-to-Decision Integrity:**
  - Extracted claims are strictly marked `is_verified: False` (never treated as verified ground-truth facts).
  - Unverified sustainability claims are represented as unverified claim nodes.
  - Verbatim excerpts, page references, and source filenames are linked without fabrication.
  - Sourcing recommendations automatically emit a `DEPENDS_ON_INCOMPLETE_DATA` edge if any allocated supplier has missing data.
  - Conflicting claims and quotes are modeled as explicit `conflict` nodes.

---

## 2. Quickstart & Verification (Windows PowerShell)

### Installation
```powershell
# From repository root (d:\ProcuraX-team)
pip install -r requirements.txt
```

### Run All 33 Automated Unit Tests
```powershell
python -m pytest -v tests/
```

### Run End-to-End Demonstration (Synthetic Benchmark)
```powershell
python demo.py
```

---

## 3. Synthetic Benchmark Dataset

A dedicated synthetic benchmark dataset is located at:
[`data/synthetic_demo_suppliers.json`](file:///d:/ProcuraX-team/data/synthetic_demo_suppliers.json)

> [!NOTE]
> All records in this dataset are clearly marked with `"is_synthetic": true`. No proprietary or real supplier data is represented.

The dataset includes realistic quotations with:
- Extracted claims, document citations, page numbers, and verbatim excerpts.
- Complete vs. incomplete data (e.g. `SUP-003` has missing `delivery_days`, `SUP-004` has missing `unit_price`).
- Environmental and sustainability claims (unverified).
- Flat vs. variable transport cost structures.

---

## 4. Integration Interfaces for Person 2 (Backend API)

Person 2 can integrate with Person 3 either via direct functional calls or via the service adapters matching Person 2's backend contracts.

```python
from procurax import (
    calculate_landed_cost,
    optimize_allocation,
    simulate_scenario,
    build_evidence_graph,
    build_procurement_graph,
    BaseOptimizationService,
    BaseGraphService,
    ProcuraXOptimizationService,
    ProcuraXGraphService,
)
```

### Direct Service Adapter Usage (FastAPI Dependency Injection)
```python
from procurax.services import ProcuraXOptimizationService, ProcuraXGraphService

# Drop-in replacement for Person 2's MockOptimizationService
optimizer_service = ProcuraXOptimizationService()
response = optimizer_service.optimize(optimization_request)

# Drop-in replacement for Person 2's MockGraphService
graph_service = ProcuraXGraphService()
graph_response = graph_service.build_graph(graph_request)
```

### Task 1: Landed-Cost Calculation
```python
def calculate_landed_cost(
    supplier: Union[Dict[str, Any], Supplier],
    quantity: int,
    additional_charges: float = 0.0,
    discount_pct: float = 0.0,
    transport_is_per_unit: Optional[bool] = None,
    target_currency: Optional[str] = None,
    currency_rates: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]
```
Returns a dictionary containing `base_cost`, `transport_cost`, `transport_cost_mode`, `total_landed_cost`, `cost_per_unit`, `currency`, `missing_cost_inputs`, and `is_complete`.

### Task 2: Supplier Allocation Optimizer
```python
def optimize_allocation(
    suppliers: List[Union[Dict[str, Any], Supplier]],
    demand: int,
    budget: Optional[float] = None,
    allow_overdelivery: bool = False,
    base_currency: Optional[str] = None,
    currency_rates: Optional[Dict[str, float]] = None,
    unavailable_suppliers: Optional[List[str]] = None,
) -> Dict[str, Any]
```
Solves exact Mixed-Integer Linear Programming (MILP) using `scipy.optimize.milp`.
Returns `status`, `is_feasible`, `allocated_demand`, `unmet_demand`, `total_cost`, `allocations`, `supplier_breakdown` (with constraint notes and exclusion reasons for every supplier), and diagnostic `explanations`.

### Task 3: Scenario Simulations
```python
def simulate_scenario(
    suppliers: List[Union[Dict[str, Any], Supplier]],
    demand: int,
    scenario: Union[Dict[str, Any], OptimizationScenario],
    budget: Optional[float] = None,
    currency_rates: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]
```
Supports:
1. `price_increase`: percentage, absolute change, or Person 2's `price_multipliers` dict.
2. `transport_cost_change`: freight adjustments by percentage, fixed amount, or `transport_multipliers` dict.
3. `capacity_reduction`: capacity drops by percentage, unit amount, or Person 2's `capacity_reductions` dict.
4. `supplier_unavailability`: factory shutdowns / vendor unavailability (`unavailable_suppliers` list).
5. `compound`: multi-factor disruption list.

Returns `baseline_summary`, `scenario_summary`, `quantity_changes` ($\Delta q_i$), `total_cost_delta` ($\Delta C$), `percentage_cost_change`, and a natural-language `narrative_explanation`.

### Task 4 & 5: Evidence-to-Decision Consistency Graph
```python
def build_evidence_graph(
    suppliers: List[Union[Dict[str, Any], Supplier]],
    allocation_result: Optional[Union[Dict[str, Any], OptimizationResponse]] = None,
    scenario_impact: Optional[Dict[str, Any]] = None,
    risks: Optional[List[Dict[str, Any]]] = None,
    conflicts: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]
```
Constructs a NetworkX directed consistency graph connecting:
- `document` $\leftarrow$ `claim` (via `EXTRACTED_FROM`)
- `evidence` $\leftarrow$ `claim` (via `SUPPORTED_BY`, preserving page & excerpt)
- `supplier` $\rightarrow$ `claim` (via `CLAIMS`)
- `supplier` $\rightarrow$ `missing_info` (via `HAS_MISSING_INFO`)
- `supplier` $\rightarrow$ `conflict` (via `HAS_CONFLICT`)
- `claim` $\rightarrow$ `cost_calculation` (via `INFLUENCES_COST`)
- `supplier_risk` $\rightarrow$ `allocation` (via `AFFECTS_ALLOCATION`)
- `cost_calculation` $\rightarrow$ `allocation` (via `DETERMINES_ALLOCATION`)
- `allocation` $\rightarrow$ `recommendation` (via `CONTRIBUTES_TO`)
- `scenario` $\rightarrow$ `recommendation` (via `SIMULATES_SHOCK_ON`)
- `recommendation` $\rightarrow$ `missing_info` (via `DEPENDS_ON_INCOMPLETE_DATA`)

Returns JSON-compatible `nodes`, `edges`, `graph_metrics`, `decision_audit`, and `metadata`.

---

## 5. Assumptions & Limitations

1. **Deterministic Sourcing on CPU:** Optimization assumes linear unit pricing and fixed transport charges per order (or linear per unit). Non-linear tiered volume discounting can be evaluated by providing tiered synthetic vendor splits.
2. **Discrete Orders:** Purchase quantities are discrete integers.
3. **Currency Conversion:** Default base currency is INR. Cross-currency comparisons require an explicit rate dictionary.
4. **Evidence Independence:** Supplier claims extracted from quotation documents are considered unverified until confirmed by independent audits or certifications.

---

## 6. Automated Test Suite (33 Tests, 100% Passing)

- `tests/test_cost.py`: 6 tests (standard landed cost, per-unit transport, missing unit price, missing transport, currency conversion, Pydantic model).
- `tests/test_optimizer.py`: 10 tests (demand fulfillment, capacity split, MOQ enforcement, budget limits, insufficient capacity, missing price exclusions, unavailable suppliers, per-unit transport, solver determinism, synthetic benchmark suite).
- `tests/test_scenarios.py`: 7 tests (price hike reallocation, transport changes, supplier unavailability, multiplier maps, capacity spillover, feasibility loss, compound disruptions).
- `tests/test_graph.py`: 7 tests (graph structure, unverified claims, unverified sustainability claims, conflict tracking, evidence citations, incomplete data flags, scenario shock modeling).
- `tests/test_services.py`: 3 tests (`ProcuraXOptimizationService`, scenario support, `ProcuraXGraphService`).
