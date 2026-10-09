"""Data models and schemas for ProcuraX supplier quotation extraction.

Matches the shared ProcuraX supplier JSON contract:
- Use null for unknown numeric values, never 0 as a placeholder.
- Extracted claims are distinguished from independently verified facts.
- Preserves source file, page, and exact source excerpts.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Claim(BaseModel):
    """An individual claim extracted from a supplier quotation document."""
    field: str = Field(
        ...,
        description="The target field name (e.g., 'unit_price', 'moq', 'capacity', 'delivery_days', 'transport_cost')."
    )
    value: Any = Field(
        default=None,
        description="The extracted value (float, int, str, list, or null)."
    )
    source_file: str = Field(
        ...,
        description="Filename of the quotation document."
    )
    source_page: Optional[int] = Field(
        default=None,
        description="Page number where the claim was found (1-indexed), or null if unknown."
    )
    source_excerpt: str = Field(
        ...,
        description="Verbatim text passage from the source document supporting this claim."
    )
    status: str = Field(
        default="extracted",
        description="Status of the claim: 'extracted', 'ambiguous', 'conflicting', or 'unverified'."
    )
    notes: Optional[str] = Field(
        default=None,
        description="Explanatory note regarding ambiguity, conflict, or special conditions."
    )
    is_verified_fact: bool = Field(
        default=False,
        description="Always False for supplier-stated claims; distinguishes claims from independently verified facts."
    )


class SupplierQuotation(BaseModel):
    """Structured supplier quotation adhering to the shared ProcuraX contract."""
    supplier_id: Optional[str] = Field(
        default=None,
        description="Unique supplier identifier (e.g. 'SUP-001') or null if absent."
    )
    supplier_name: Optional[str] = Field(
        default=None,
        description="Full legal or trading name of the supplier."
    )
    product_name: Optional[str] = Field(
        default=None,
        description="Name of the quoted product/item."
    )
    unit_price: Optional[float] = Field(
        default=None,
        description="Unit price per item. Null if unknown (never 0)."
    )
    currency: Optional[str] = Field(
        default=None,
        description="ISO currency code (e.g., 'INR', 'USD', 'EUR')."
    )
    moq: Optional[int] = Field(
        default=None,
        description="Minimum order quantity in units. Null if unknown (never 0)."
    )
    capacity: Optional[int] = Field(
        default=None,
        description="Maximum production or supply capacity in units. Null if unknown (never 0)."
    )
    delivery_days: Optional[int] = Field(
        default=None,
        description="Promised delivery lead time in calendar or business days. Null if unknown."
    )
    transport_cost: Optional[float] = Field(
        default=None,
        description="Transportation, freight, or shipping charge. Null if unknown (never 0 unless free)."
    )
    discount_terms: Optional[str] = Field(
        default=None,
        description="Volume or early-payment discount structure stated in quotation."
    )
    sustainability_claims: List[str] = Field(
        default_factory=list,
        description="List of sustainability or environmental certifications/claims."
    )
    missing_fields: List[str] = Field(
        default_factory=list,
        description="List of standard procurement fields that are absent or unstated in the quotation."
    )
    ambiguous_fields: List[str] = Field(
        default_factory=list,
        description="List of fields where statements are vague, conditional, or subject to variation."
    )
    conflicting_fields: List[str] = Field(
        default_factory=list,
        description="List of fields where multiple contradictory values or conditions were stated."
    )
    claims: List[Claim] = Field(
        default_factory=list,
        description="List of evidence-backed claims extracted from the source document."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extraction metadata (model name, synthetic flag, confidence, fallback flag, etc.)."
    )

    def to_contract_dict(self) -> Dict[str, Any]:
        """Convert to the exact shared ProcuraX supplier JSON dictionary."""
        return self.model_dump(mode="json")
