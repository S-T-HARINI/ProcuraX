from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ClaimStatus(str, Enum):
    EXTRACTED = "extracted"
    VERIFIED = "verified"
    CONFLICTING = "conflicting"
    AMBIGUOUS = "ambiguous"
    MISSING = "missing"


class Claim(BaseModel):
    field: str
    value: Any = None
    source_file: Optional[str] = None
    source_page: Optional[int] = None
    source_excerpt: Optional[str] = None
    status: str = "extracted"


class SupplierQuote(BaseModel):
    supplier_id: str
    supplier_name: str
    product_name: Optional[str] = None
    unit_price: Optional[float] = Field(
        default=None, description="Unit price. None if unknown; never 0 as a default fallback."
    )
    currency: Optional[str] = "INR"
    moq: Optional[int] = Field(
        default=None, description="Minimum order quantity. None if unknown."
    )
    capacity: Optional[int] = Field(
        default=None, description="Supplier max capacity. None if unknown."
    )
    delivery_days: Optional[int] = Field(
        default=None, description="Delivery lead time in days. None if unknown."
    )
    transport_cost: Optional[float] = Field(
        default=None, description="Transport/logistics cost. None if unknown."
    )
    discount_terms: Optional[str] = None
    sustainability_claims: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    ambiguous_fields: List[str] = Field(default_factory=list)
    conflicting_fields: List[str] = Field(default_factory=list)
    claims: List[Claim] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentPage(BaseModel):
    page_number: int
    text: str


class DocumentParseResponse(BaseModel):
    filename: str
    file_type: str
    total_pages: int
    pages: List[DocumentPage]
    raw_text: str


class ExtractRequest(BaseModel):
    filename: Optional[str] = "supplier_quotation.pdf"
    parsed_pages: Optional[List[DocumentPage]] = None
    raw_text: Optional[str] = None
    use_mock: bool = False
    model: str = "gemma4:e2b"


class ExtractResponse(BaseModel):
    suppliers: List[SupplierQuote]
    missing_fields_summary: List[str] = Field(default_factory=list)
    conflicts_summary: List[str] = Field(default_factory=list)
    is_mock: bool = True
    message: str = "Extraction performed."


class OptimizationScenario(BaseModel):
    type: str = "price_increase"  # "price_increase" | "capacity_reduction" | "compound"
    supplier_id: Optional[str] = None
    percentage: float = 0.0
    reduction_amount: Optional[int] = None
    scenarios: Optional[List[Dict[str, Any]]] = None


class OptimizationRequest(BaseModel):
    suppliers: List[SupplierQuote]
    target_demand: int = Field(gt=0, description="Total units required")
    budget_limit: Optional[float] = Field(
        default=None, description="Optional maximum budget constraint"
    )
    scenario: Optional[OptimizationScenario] = None


class SupplierAllocation(BaseModel):
    supplier_id: str
    supplier_name: str
    allocated_quantity: int
    cost_breakdown: Optional[Dict[str, Any]] = None
    capacity: Optional[int] = None
    moq: Optional[int] = None
    share_of_demand_pct: float = 0.0


class OptimizationResponse(BaseModel):
    status: str = "optimal"  # "optimal" | "infeasible" | "suboptimal"
    is_feasible: bool = True
    target_demand: int
    total_allocated_quantity: int
    unmet_demand: int = 0
    total_landed_cost: Optional[float] = None
    currency: Optional[str] = "INR"
    budget_limit: Optional[float] = None
    budget_utilized_pct: Optional[float] = None
    allocations: List[SupplierAllocation] = Field(default_factory=list)
    unassigned_suppliers: List[str] = Field(default_factory=list)
    explanations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    scenario_impact: Optional[Dict[str, Any]] = None
    is_mock: bool = False
    message: str = "Optimization complete."


class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # "document", "claim", "supplier", "cost", "risk", "decision"
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str
    relation_type: str


class GraphRequest(BaseModel):
    suppliers: List[SupplierQuote]
    optimization_result: Optional[OptimizationResponse] = None
    scenario_impact: Optional[Dict[str, Any]] = None


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_mock: bool = False
    message: str = "Evidence-to-decision graph constructed."


class WorkflowRequest(BaseModel):
    document_filename: Optional[str] = "supplier_quotation.pdf"
    document_text: Optional[str] = None
    target_demand: int = Field(default=500, gt=0)
    budget_limit: Optional[float] = None
    scenario: Optional[OptimizationScenario] = None
    use_mock_extraction: bool = False


class WorkflowResponse(BaseModel):
    document: Dict[str, Any]
    extraction: ExtractResponse
    optimization: OptimizationResponse
    graph: GraphResponse
    summary: str
