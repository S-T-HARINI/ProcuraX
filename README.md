# ProcuraX — Procurement Optimization, Scenarios, and Graph Engine

**Branch:** `feature/optimization-graph` (Person 3)  
**Role:** Landed-Cost Calculation, Supplier Allocation Optimizer, Scenario Simulations, Evidence-to-Decision Consistency Graph, and Service Adapters.

---

## 1. Overview & Core Innovations

All modules run **purely on CPU**, deterministically, without requiring Gemma 4, GPU acceleration, or local Ollama instances.

### Key Principles & Guarantees
- **Shared JSON Contract Compliance:** Uses the shared supplier schema from the Universal Project Prompt.
- **Honest Null Handling:** Unknown numeric values are preserved as `null`, never replaced with zero.
- **Explicit Transport Cost Assumptions:**
  - *Fixed Per Shipment (Default):* Logistics charge is a flat freight fee per delivery order batch, independent of units within capacity (`transport_is_per_unit=False` or `transport_cost_type="fixed_per_shipment"`).
  - *Variable Per Unit:* Freight is charged per individual unit (`transport_is_per_unit=True` or `transport_cost_type="per_unit"`).
  - Both modes are supported in `calculate_landed_cost` and the MILP solver.
- **Supplier Breakdown & Exclusion Transparency:** Every supplier evaluated receives an explicit status (`allocated`, `unassigned`, or `excluded`) and constraint/exclusion reason (e.g. missing price, capacity < MOQ, non-competitive cost, or marked unavailable).
- **Evidence-to-Decision Integrity:**
  - Extracted claims are strictly marked `is_verified: False`.
  - Unverified sustainability claims are represented explicitly as unverified claim nodes.
  - Sourcing recommendations automatically emit a `DEPENDS_ON_INCOMPLETE_DATA` edge if any allocated supplier has missing attributes.
  - Conflicting claims and quotes are modeled as explicit `conflict` nodes.

---

## 2. Windows PowerShell Setup & Execution

### Prerequisites
- Python 3.10+ (tested on Python 3.13.5)

### Installation
```powershell
# From repository root (d:\ProcuraX-team)
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

Person 2 can integrate via direct function calls or via the `BaseOptimizationService` / `BaseGraphService` service adapters.

```python
from procurax import (
    calculate_landed_cost,
    optimize_allocation,
    simulate_scenario,
    build_procurement_graph,
    BaseOptimizationService,
    BaseGraphService,
    ProcuraXOptimizationService,
    ProcuraXGraphService,
    Supplier,
    CostBreakdown,
    OptimizationSummary,
    ScenarioImpact,
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
- Distinguishes total landed cost from cost per unit.
- If `unit_price` or `transport_cost` is `null`, returns `is_complete: False` without assuming zero.
- Output includes `transport_cost_mode`, `base_cost`, `transport_cost`, `total_landed_cost`, `cost_per_unit`, `currency`, `missing_cost_inputs`.

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
- Solves exact Mixed-Integer Linear Programming (MILP) using `scipy.optimize.milp`.
- Respects:
  - Total demand
  - Supplier capacity upper bounds
  - Minimum order quantity (MOQ) step condition ($q_i \ge \text{moq}_i \cdot y_i$)
  - Spending budget limits ($\sum \text{cost}_i \le \text{budget}$)
  - Missing or invalid supplier information
  - Supplier availability status
- Returns `status`, `is_feasible`, `allocated_demand`, `unmet_demand`, `total_cost`, `allocations`, `supplier_breakdown` (with constraint notes and exclusion reasons), and diagnostic `explanations`.

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
Supported scenario disruptions:
1. `price_increase`: by percentage, fixed amount, or `price_multipliers` map.
2. `transport_cost_change`: freight adjustments by percentage, fixed amount, or `transport_multipliers` map.
3. `capacity_reduction`: capacity cuts by percentage, fixed unit amount, or `capacity_reductions` map.
4. `supplier_unavailability`: supplier factory shutdown / unavailability (`unavailable_suppliers` list).
5. `compound`: multi-factor disruption list.

Returns `baseline_summary`, `scenario_summary`, `quantity_changes` ($\Delta q_i$), `total_cost_delta` ($\Delta C$), `percentage_cost_change`, and a natural-language `narrative_explanation`.

### Task 4: Evidence-to-Decision Consistency Graph
```python
def build_procurement_graph(
    suppliers: List[Union[Dict[str, Any], Supplier]],
    allocation: Union[Dict[str, Any], OptimizationResponse],
    risks: Optional[List[Dict[str, Any]]] = None,
    conflicts: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]
```
- Uses NetworkX (`nx.DiGraph`).
- Links:
  - `document` $\leftarrow$ `claim` (via `EXTRACTED_FROM`)
  - `evidence` $\leftarrow$ `claim` (via `SUPPORTED_BY`, preserving page & excerpt)
  - `supplier` $\rightarrow$ `claim` (via `CLAIMS`)
  - `supplier` $\rightarrow$ `missing_info` (via `HAS_MISSING_INFO`)
  - `supplier` $\rightarrow$ `conflict` (via `HAS_CONFLICT`)
  - `claim` $\rightarrow$ `cost_calculation` (via `INFLUENCES_COST`)
  - `supplier_risk` $\rightarrow$ `allocation` (via `AFFECTS_ALLOCATION`)
  - `cost_calculation` $\rightarrow$ `allocation` (via `DETERMINES_ALLOCATION`)
  - `allocation` $\rightarrow$ `recommendation` (via `CONTRIBUTES_TO`)
  - `recommendation` $\rightarrow$ `missing_info` (via `DEPENDS_ON_INCOMPLETE_DATA`)
- Returns JSON-compatible `nodes`, `edges`, `graph_metrics`, and `decision_audit`.

---

## 4. Assumptions & Limitations

1. **Deterministic Sourcing on CPU:** Optimization assumes linear unit pricing and fixed transport charges per order (or linear per unit). Non-linear tiered pricing can be modeled by adding tiered synthetic supplier options.
2. **Discrete Orders:** Quantities are strictly integers.
3. **Currency Conversion:** Default base currency is INR. Cross-currency comparisons require an explicit rate dictionary.
4. **Evidence Independence:** Supplier quotations provide unverified claims. Verification requires external audit documents (e.g. third-party audit certificates).

---

## 5. Automated Test Suite (30 Tests, 100% Passing)

- `tests/test_cost.py`: 6 tests (standard landed cost, per-unit transport, missing unit price, missing transport, currency conversion, Pydantic model).
- `tests/test_optimizer.py`: 8 tests (demand fulfillment, capacity split, MOQ enforcement, budget limits, insufficient capacity, missing price exclusions, unavailable suppliers, per-unit transport).
- `tests/test_scenarios.py`: 7 tests (price hike reallocation, transport changes, supplier unavailability, multiplier maps, capacity spillover, feasibility loss, compound disruptions).
- `tests/test_graph.py`: 6 tests (graph structure, unverified claims, unverified sustainability claims, conflict tracking, evidence citations, incomplete data flags).
- `tests/test_services.py`: 3 tests (`ProcuraXOptimizationService`, scenario support, `ProcuraXGraphService`).
