"""Validation, reconciliation, and post-processing for supplier quotation extraction.

Ensures adherence to ProcuraX rules:
1. Null used for unknown numeric values, never 0 as a placeholder.
2. Preserves evidence (source_file, source_page, verbatim excerpt).
3. Distinguishes extracted claims from independently verified facts (is_verified_fact=False).
4. Reconciles missing, ambiguous, and conflicting fields deterministically.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from procurax.extraction.schema import Claim, SupplierQuotation


CORE_PROCUREMENT_FIELDS = [
    "unit_price",
    "currency",
    "moq",
    "capacity",
    "delivery_days",
    "transport_cost"
]


def extract_json_from_text(raw_text: str) -> Dict[str, Any]:
    """Safely extract a JSON object from raw LLM output text.
    
    Handles markdown code blocks (```json ... ```), trailing commas, and leading/trailing text.
    """
    cleaned = raw_text.strip()
    
    # Try direct parse first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    # Try finding markdown code block ```json ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if match:
        block = match.group(1)
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            sanitized = re.sub(r",\s*([\}\]])", r"\1", block)
            try:
                return json.loads(sanitized)
            except json.JSONDecodeError:
                pass
            
    # Try finding first outer { and last outer }
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start:end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            sanitized = re.sub(r",\s*([\}\]])", r"\1", candidate)
            try:
                return json.loads(sanitized)
            except json.JSONDecodeError:
                pass

    raise ValueError(f"Could not parse valid JSON from model response: {raw_text[:200]}...")


def heuristic_extract_supplier_data(
    document_text: str,
    source_file: str,
    source_pages: Optional[Union[int, List[int], Dict[int, str]]] = None,
    engine_label: str = "HEURISTIC_FALLBACK (Rule-Based Parser)"
) -> SupplierQuotation:
    """Extract procurement claims deterministically using pattern heuristics from document text.
    
    Used when the LLM is offline or outputs malformed text, ensuring verbatim
    excerpts and real page numbers from the source document are preserved.
    """
    lines = [line.strip() for line in (document_text or "").splitlines() if line.strip()]
    
    extracted_data: Dict[str, Any] = {
        "supplier_id": None,
        "supplier_name": None,
        "product_name": None,
        "unit_price": None,
        "currency": None,
        "moq": None,
        "capacity": None,
        "delivery_days": None,
        "transport_cost": None,
        "discount_terms": None,
        "sustainability_claims": [],
        "missing_fields": [],
        "ambiguous_fields": [],
        "conflicting_fields": [],
        "claims": []
    }
    
    claims_list: List[Dict[str, Any]] = []
    
    for line in lines:
        lower = line.lower()
        
        # Supplier ID
        if re.search(r"supplier\s*id\s*:", lower):
            m = re.search(r"supplier\s*id\s*:\s*([A-Za-z0-9_-]+)", line, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                extracted_data["supplier_id"] = val
                claims_list.append({
                    "field": "supplier_id",
                    "value": val,
                    "source_excerpt": line,
                    "status": "extracted"
                })
        # Supplier Name
        elif re.search(r"supplier(?:\s*name)?\s*:", lower):
            m = re.search(r"supplier(?:\s*name)?\s*:\s*([^\n\r,]+)", line, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                extracted_data["supplier_name"] = val
                claims_list.append({
                    "field": "supplier_name",
                    "value": val,
                    "source_excerpt": line,
                    "status": "extracted"
                })
        # Product / Item
        elif re.search(r"(?:product|item)(?:\s*name)?\s*:", lower):
            m = re.search(r"(?:product|item)(?:\s*name)?\s*:\s*([^\n\r]+)", line, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                extracted_data["product_name"] = val
                claims_list.append({
                    "field": "product_name",
                    "value": val,
                    "source_excerpt": line,
                    "status": "extracted"
                })
        # Unit Price
        if re.search(r"(?:unit\s*price|base\s*price|rate)\s*:", lower):
            # Check currency
            curr_match = re.search(r"\b(INR|USD|EUR|GBP|Rs\.?)\b", line, re.IGNORECASE)
            if curr_match:
                extracted_data["currency"] = curr_match.group(1).upper()
            elif "$" in line:
                extracted_data["currency"] = "USD"
            elif "₹" in line:
                extracted_data["currency"] = "INR"

            # Check price value
            num_m = re.search(r"(\d+(?:\.\d+)?)", line)
            if num_m:
                val = float(num_m.group(1))
                is_conflicting = "rush" in lower or "urgent" in lower or "contradictory" in lower
                if is_conflicting or (extracted_data["unit_price"] is not None and extracted_data["unit_price"] != val):
                    claims_list.append({
                        "field": "unit_price",
                        "value": val,
                        "source_excerpt": line,
                        "status": "conflicting",
                        "notes": "Contradictory or rush pricing quote"
                    })
                    if "unit_price" not in extracted_data["conflicting_fields"]:
                        extracted_data["conflicting_fields"].append("unit_price")
                else:
                    extracted_data["unit_price"] = val
                    claims_list.append({
                        "field": "unit_price",
                        "value": val,
                        "source_excerpt": line,
                        "status": "extracted"
                    })
        # MOQ
        elif re.search(r"(?:moq|minimum\s*order(?:\s*quantity)?)\s*:", lower):
            num_m = re.search(r"(\d+)", line)
            if num_m:
                val = int(num_m.group(1))
                extracted_data["moq"] = val
                claims_list.append({
                    "field": "moq",
                    "value": val,
                    "source_excerpt": line,
                    "status": "extracted"
                })
        # Capacity
        elif re.search(r"(?:capacity|production\s*capacity|monthly\s*capacity)\s*:", lower):
            num_m = re.search(r"(\d+)", line)
            if num_m:
                val = int(num_m.group(1))
                extracted_data["capacity"] = val
                claims_list.append({
                    "field": "capacity",
                    "value": val,
                    "source_excerpt": line,
                    "status": "extracted"
                })
        # Delivery / Lead Time
        elif re.search(r"(?:delivery(?:\s*lead\s*time)?|lead\s*time)\s*:", lower):
            # Check for range/ambiguity (e.g., 5 to 14 days or variable)
            is_ambiguous = bool(re.search(r"\bto\b|\bvariable\b|\bbacklog\b|\bapprox\b|-", lower))
            num_m = re.search(r"(\d+)", line)
            if is_ambiguous:
                extracted_data["ambiguous_fields"].append("delivery_days")
                extracted_data["delivery_days"] = None
                claims_list.append({
                    "field": "delivery_days",
                    "value": line.split(":", 1)[1].strip() if ":" in line else line,
                    "source_excerpt": line,
                    "status": "ambiguous",
                    "notes": "Variable delivery range"
                })
            elif num_m:
                val = int(num_m.group(1))
                extracted_data["delivery_days"] = val
                claims_list.append({
                    "field": "delivery_days",
                    "value": val,
                    "source_excerpt": line,
                    "status": "extracted"
                })
        # Transport / Freight
        elif re.search(r"(?:transport(?:ation)?|freight|shipping)(?:\s*(?:cost|charge|charges))?\s*:", lower):
            is_unspecified = any(w in lower for w in ["tbd", "to be determined", "not included", "pending"])
            if is_unspecified:
                extracted_data["transport_cost"] = None
                claims_list.append({
                    "field": "transport_cost",
                    "value": None,
                    "source_excerpt": line,
                    "status": "extracted",
                    "notes": "Freight cost pending or not included"
                })
            else:
                num_m = re.search(r"(\d+(?:\.\d+)?)", line)
                if num_m:
                    val = float(num_m.group(1))
                    extracted_data["transport_cost"] = val
                    claims_list.append({
                        "field": "transport_cost",
                        "value": val,
                        "source_excerpt": line,
                        "status": "extracted"
                    })
        # Sustainability
        elif re.search(r"(?:sustainability|certified|recyclable|recycled|fsc|ocean\s*bound)", lower):
            extracted_data["sustainability_claims"].append(line)
            claims_list.append({
                "field": "sustainability_claims",
                "value": line,
                "source_excerpt": line,
                "status": "extracted"
            })
            
    extracted_data["claims"] = claims_list
    
    return verify_and_reconcile_quotation(
        raw_data=extracted_data,
        document_text=document_text,
        source_file=source_file,
        source_pages=source_pages,
        metadata_extra={
            "extraction_engine": engine_label,
            "is_synthetic": False,
            "fallback_triggered": True
        }
    )


def detect_page_number(
    excerpt: str,
    document_text: str,
    source_pages: Optional[Union[int, List[int], Dict[int, str]]] = None
) -> Optional[int]:
    """Determine the page number for a given excerpt.
    
    Supports:
    - Explicit integer page
    - Dictionary mapping page numbers to page text
    - Page markers within document_text (e.g., '--- Page 2 ---' or '[Page 2]')
    """
    if isinstance(source_pages, int):
        return source_pages
    
    if isinstance(source_pages, dict):
        # Search which page text contains the excerpt
        norm_excerpt = excerpt.lower().strip()
        for page_num, page_content in source_pages.items():
            if norm_excerpt in page_content.lower():
                return int(page_num)
        return list(source_pages.keys())[0] if source_pages else 1

    # Check for in-text page markers
    page_markers = list(re.finditer(r"(?:---|===|\[)\s*Page\s+(\d+)\s*(?:---|===|\])", document_text, re.IGNORECASE))
    if page_markers and excerpt:
        pos = document_text.lower().find(excerpt.lower())
        if pos != -1:
            current_page = 1
            for marker in page_markers:
                if marker.start() <= pos:
                    current_page = int(marker.group(1))
                else:
                    break
            return current_page

    return 1 if source_pages is not None else None


def clean_numeric(val: Any, target_type: type = float) -> Optional[Union[float, int]]:
    """Convert mixed string/numeric values to clean numeric or None."""
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        return target_type(val)
    if isinstance(val, str):
        # Remove common currency symbols, commas, and trailing words
        clean_str = re.sub(r"[^\d.-]", "", val.strip())
        if not clean_str or clean_str in ("-", ".", "-."):
            return None
        try:
            return target_type(clean_str)
        except ValueError:
            return None
    return None


def verify_and_reconcile_quotation(
    raw_data: Dict[str, Any],
    document_text: str,
    source_file: str,
    source_pages: Optional[Union[int, List[int], Dict[int, str]]] = None,
    metadata_extra: Optional[Dict[str, Any]] = None
) -> SupplierQuotation:
    """Post-process, validate, and normalize the extracted quotation dictionary.
    
    Guarantees:
    - Null for unknown numbers, never 0 unless explicitly stated as zero/free.
    - Missing fields tracked accurately.
    - Conflicting and ambiguous claims flagged.
    - Exact source excerpts and page numbers preserved.
    - Extracted claims tagged as unverified facts.
    """
    doc_lower = document_text.lower()
    
    # 1. Clean core fields
    unit_price = clean_numeric(raw_data.get("unit_price"), float)
    moq = clean_numeric(raw_data.get("moq"), int)
    capacity = clean_numeric(raw_data.get("capacity"), int)
    delivery_days = clean_numeric(raw_data.get("delivery_days"), int)
    transport_cost = clean_numeric(raw_data.get("transport_cost"), float)
    
    currency = raw_data.get("currency")
    if currency and isinstance(currency, str):
        currency = currency.strip().upper()
        # Clean currency codes
        curr_map = {"$": "USD", "₹": "INR", "€": "EUR", "£": "GBP", "RS": "INR", "RUPEES": "INR"}
        currency = curr_map.get(currency, currency)
    else:
        currency = None

    # 2. Check for false zero (Rule: Use null for unknown numeric values, not zero)
    # If 0 is present, check if document explicitly mentions zero/free
    zero_keywords = ["0", "zero", "free", "included", "no charge", "complimentary", "nil"]
    
    if transport_cost == 0.0:
        has_free_shipping = any(kw in doc_lower for kw in ["free shipping", "free delivery", "transport: 0", "shipping: free", "no charge"])
        if not has_free_shipping:
            transport_cost = None
            
    if unit_price == 0.0:
        unit_price = None

    if moq == 0:
        has_no_moq = any(kw in doc_lower for kw in ["no moq", "moq: none", "0 moq", "minimum order: none"])
        if not has_no_moq:
            moq = None

    # 3. Process claims
    raw_claims = raw_data.get("claims", [])
    processed_claims: List[Claim] = []
    
    for c in raw_claims:
        if not isinstance(c, dict):
            continue
        field_name = str(c.get("field", "unspecified")).strip().lower()
        # Normalize common field names
        if "price" in field_name:
            norm_field = "unit_price"
        elif "moq" in field_name or "minimum order" in field_name:
            norm_field = "moq"
        elif "capacity" in field_name:
            norm_field = "capacity"
        elif "delivery" in field_name or "lead time" in field_name:
            norm_field = "delivery_days"
        elif "transport" in field_name or "freight" in field_name or "shipping" in field_name:
            norm_field = "transport_cost"
        elif "supplier" in field_name:
            norm_field = "supplier_name"
        elif "product" in field_name:
            norm_field = "product_name"
        else:
            norm_field = field_name
            
        excerpt = str(c.get("source_excerpt", "")).strip()
        status = str(c.get("status", "extracted")).lower()
        if status not in ("extracted", "ambiguous", "conflicting"):
            status = "extracted"

        # Determine page number for excerpt
        page_num = detect_page_number(excerpt, document_text, source_pages)
        
        claim_obj = Claim(
            field=norm_field,
            value=c.get("value"),
            source_file=source_file,
            source_page=page_num,
            source_excerpt=excerpt,
            status=status,
            notes=c.get("notes"),
            is_verified_fact=False  # Extracted claims are unverified supplier claims
        )
        processed_claims.append(claim_obj)

    # 4. Check for conflicting claims (e.g. multiple distinct values for same field)
    conflicting_fields: List[str] = list(raw_data.get("conflicting_fields", []))
    ambiguous_fields: List[str] = list(raw_data.get("ambiguous_fields", []))
    
    # Detect conflicting claims algorithmically
    claims_by_field: Dict[str, List[Claim]] = {}
    for cl in processed_claims:
        claims_by_field.setdefault(cl.field, []).append(cl)

    for f_name, cl_list in claims_by_field.items():
        if len(cl_list) > 1:
            values = set()
            for item in cl_list:
                v = item.value
                if isinstance(v, (int, float)):
                    values.add(round(float(v), 2))
                elif isinstance(v, str):
                    values.add(v.strip().lower())
            if len(values) > 1:
                if f_name not in conflicting_fields:
                    conflicting_fields.append(f_name)
                for item in cl_list:
                    if item.status != "conflicting":
                        item.status = "conflicting"
                        if not item.notes:
                            item.notes = f"Multiple differing values extracted for {f_name}."

    # Mark ambiguous claims in ambiguous_fields
    for cl in processed_claims:
        if cl.status == "ambiguous" and cl.field not in ambiguous_fields:
            ambiguous_fields.append(cl.field)
        elif cl.status == "conflicting" and cl.field not in conflicting_fields:
            conflicting_fields.append(cl.field)

    # 5. Missing fields reconciliation
    missing_fields: List[str] = []
    field_values = {
        "unit_price": unit_price,
        "currency": currency,
        "moq": moq,
        "capacity": capacity,
        "delivery_days": delivery_days,
        "transport_cost": transport_cost,
    }
    
    for f, val in field_values.items():
        if val is None:
            missing_fields.append(f)

    # Deduplicate lists
    missing_fields = sorted(list(set(missing_fields)))
    ambiguous_fields = sorted(list(set(ambiguous_fields)))
    conflicting_fields = sorted(list(set(conflicting_fields)))

    # 6. Sustainability claims
    sustainability = raw_data.get("sustainability_claims", [])
    if isinstance(sustainability, str):
        sustainability = [sustainability]
    elif not isinstance(sustainability, list):
        sustainability = []

    # 7. Metadata
    metadata = raw_data.get("metadata", {})
    if metadata_extra:
        metadata.update(metadata_extra)
    metadata.setdefault("is_synthetic", False)
    metadata.setdefault("unverified_claims_warning", "Claims reflect supplier statements and have not been independently verified.")

    return SupplierQuotation(
        supplier_id=raw_data.get("supplier_id"),
        supplier_name=raw_data.get("supplier_name"),
        product_name=raw_data.get("product_name"),
        unit_price=unit_price,
        currency=currency,
        moq=moq,
        capacity=capacity,
        delivery_days=delivery_days,
        transport_cost=transport_cost,
        discount_terms=raw_data.get("discount_terms"),
        sustainability_claims=sustainability,
        missing_fields=missing_fields,
        ambiguous_fields=ambiguous_fields,
        conflicting_fields=conflicting_fields,
        claims=processed_claims,
        metadata=metadata
    )
