"""
Data contract models for ProcuraX.
Complies with the Universal Project Prompt shared supplier JSON contract.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Claim(BaseModel):
    field: str
    value: Any
    source_file: Optional[str] = None
    source_page: Optional[int] = None
    source_excerpt: Optional[str] = None
    status: str = "extracted"  # "extracted", "unverified", "verified"


class Supplier(BaseModel):
    supplier_id: str
    supplier_name: str
    product_name: Optional[str] = None
    unit_price: Optional[float] = None
    currency: Optional[str] = "INR"
    moq: Optional[int] = None
    capacity: Optional[int] = None
    delivery_days: Optional[int] = None
    transport_cost: Optional[float] = None
    sustainability_claims: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    claims: List[Claim] = Field(default_factory=list)


class CostBreakdown(BaseModel):
    supplier_id: str
    supplier_name: str
    quantity: int
    unit_price: Optional[float] = None
    base_cost: Optional[float] = None
    transport_cost: Optional[float] = None
    additional_charges: float = 0.0
    discounts: float = 0.0
    total_landed_cost: Optional[float] = None
    cost_per_unit: Optional[float] = None
    currency: Optional[str] = None
    missing_cost_inputs: List[str] = Field(default_factory=list)
    is_complete: bool = True


class AllocationResult(BaseModel):
    supplier_id: str
    supplier_name: str
    allocated_quantity: int
    cost_breakdown: Optional[CostBreakdown] = None
    capacity: Optional[int] = None
    moq: Optional[int] = None
    share_of_demand_pct: float = 0.0


class OptimizationSummary(BaseModel):
    status: str  # "optimal", "infeasible", "partial"
    is_feasible: bool
    requested_demand: int
    allocated_demand: int
    unmet_demand: int
    total_cost: Optional[float] = None
    currency: Optional[str] = None
    budget: Optional[float] = None
    budget_utilized_pct: Optional[float] = None
    explanations: List[str] = Field(default_factory=list)
    allocations: List[AllocationResult] = Field(default_factory=list)
    unassigned_suppliers: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ScenarioImpact(BaseModel):
    scenario_type: str
    parameters: Dict[str, Any]
    baseline_status: str
    scenario_status: str
    is_feasible: bool
    total_cost_delta: Optional[float] = None
    percentage_cost_change: Optional[float] = None
    quantity_changes: Dict[str, int] = Field(default_factory=dict)
    narrative_explanation: str
    baseline_summary: OptimizationSummary
    scenario_summary: OptimizationSummary
