from enum import Enum
from typing import Any, Optional
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
    source_file: str
    source_page: Optional[int] = None
    source_excerpt: str
    status: ClaimStatus = ClaimStatus.EXTRACTED


class SupplierQuote(BaseModel):
    supplier_id: str
    supplier_name: str
    product_name: str
    unit_price: Optional[float] = Field(
        default=None, description="Unit price. None if unknown; never 0 as a default fallback."
    )
    currency: str = "INR"
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
    sustainability_claims: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)


class DocumentPage(BaseModel):
    page_number: int
    text: str


class DocumentParseResponse(BaseModel):
    filename: str
    file_type: str
    total_pages: int
    pages: list[DocumentPage]
    raw_text: str


class ExtractRequest(BaseModel):
    filename: Optional[str] = "supplier_quotation.pdf"
    parsed_pages: Optional[list[DocumentPage]] = None
    raw_text: Optional[str] = None


class ExtractResponse(BaseModel):
    suppliers: list[SupplierQuote]
    missing_fields_summary: list[str] = Field(default_factory=list)
    conflicts_summary: list[str] = Field(default_factory=list)
    is_mock: bool = True
    message: str = "Extraction performed."


class OptimizationScenario(BaseModel):
    price_multipliers: dict[str, float] = Field(
        default_factory=dict,
        description="Map of supplier_id to price multiplier (e.g., {'SUP-001': 1.15})"
    )
    capacity_reductions: dict[str, float] = Field(
        default_factory=dict,
        description="Map of supplier_id to capacity reduction fraction (e.g., {'SUP-001': 0.20} for 20% reduction)"
    )


class OptimizationRequest(BaseModel):
    suppliers: list[SupplierQuote]
    target_demand: int = Field(gt=0, description="Total units required")
    budget_limit: Optional[float] = Field(
        default=None, description="Optional maximum budget constraint"
    )
    scenario: Optional[OptimizationScenario] = None


class SupplierAllocation(BaseModel):
    supplier_id: str
    supplier_name: str
    allocated_quantity: int
    effective_unit_price: float
    unit_transport_cost: float
    landed_cost: float
    capacity_utilization_pct: float


class OptimizationResponse(BaseModel):
    status: str = "optimal"  # "optimal" | "infeasible" | "suboptimal"
    target_demand: int
    total_allocated_quantity: int
    total_landed_cost: float
    budget_limit: Optional[float] = None
    budget_exceeded: bool = False
    allocations: list[SupplierAllocation]
    unmet_demand: int = 0
    warnings: list[str] = Field(default_factory=list)
    is_mock: bool = True
    message: str = "Optimization process completed."


class NodeType(str, Enum):
    DOCUMENT = "document"
    CLAIM = "claim"
    SUPPLIER = "supplier"
    COST = "cost"
    RISK = "risk"
    DECISION = "decision"


class GraphNode(BaseModel):
    id: str
    label: str
    type: NodeType
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str
    relation_type: str


class GraphRequest(BaseModel):
    suppliers: list[SupplierQuote]
    optimization_result: Optional[OptimizationResponse] = None


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    is_mock: bool = True
    message: str = "Evidence-to-decision graph constructed."
