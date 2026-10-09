"""Supplier information extraction engine powered by Gemma 4 E2B via Ollama.

Exports the core extraction function:
    extract_supplier_data(document_text, source_file, source_pages=None, ...)
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

try:
    from ollama import chat, ResponseError
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    ResponseError = Exception

from procurax.extraction.mock_data import mock_extract_supplier_data
from procurax.extraction.prompts import (
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_USER_PROMPT_TEMPLATE,
)
from procurax.extraction.schema import SupplierQuotation
from procurax.extraction.validator import (
    extract_json_from_text,
    verify_and_reconcile_quotation,
)

logger = logging.getLogger("procurax.extraction")


def extract_supplier_data(
    document_text: str,
    source_file: str,
    source_pages: Optional[Union[int, List[int], Dict[int, str]]] = None,
    use_mock: bool = False,
    model: str = "gemma4:e2b",
    allow_fallback: bool = True,
) -> Dict[str, Any]:
    """Extract structured supplier quotation data grounded in source evidence.

    Args:
        document_text: Full raw text of the supplier quotation document.
        source_file: Filename of the source document (e.g., 'supplier_a.pdf').
        source_pages: Optional page number (int), list of pages, or {page_num: text} mapping.
        use_mock: If True, uses deterministic synthetic mock extraction immediately.
        model: Ollama model name, defaults to 'gemma4:e2b'.
        allow_fallback: If True and model extraction fails, falls back to mock extractor.

    Returns:
        Dict conforming strictly to the shared ProcuraX supplier JSON contract:
        {
            "supplier_id": str | null,
            "supplier_name": str | null,
            "product_name": str | null,
            "unit_price": float | null,
            "currency": str | null,
            "moq": int | null,
            "capacity": int | null,
            "delivery_days": int | null,
            "transport_cost": float | null,
            "discount_terms": str | null,
            "sustainability_claims": list[str],
            "missing_fields": list[str],
            "ambiguous_fields": list[str],
            "conflicting_fields": list[str],
            "claims": list[dict],
            "metadata": dict
        }
    """
    # 1. Check if mock mode was explicitly requested
    if use_mock:
        quotation = mock_extract_supplier_data(
            document_text=document_text,
            source_file=source_file,
            source_pages=source_pages,
        )
        return quotation.to_contract_dict()

    # 2. Check if Ollama package is installed
    if not OLLAMA_AVAILABLE:
        if allow_fallback:
            logger.warning("Ollama library not available. Falling back to mock extractor.")
            quotation = mock_extract_supplier_data(document_text, source_file, source_pages)
            quotation.metadata["fallback_triggered"] = True
            quotation.metadata["fallback_reason"] = "ollama library not installed"
            return quotation.to_contract_dict()
        raise RuntimeError("Ollama library is not installed in the environment.")

    # 3. Call Gemma 4 E2B via Ollama
    user_prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(
        source_file=source_file,
        document_text=document_text.strip(),
    )

    try:
        response = chat(
            model=model,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            format="json",
        )
        raw_content = response.message.content
        parsed_json = extract_json_from_text(raw_content)

        # 4. Validate, reconcile, and ground extracted claims
        quotation = verify_and_reconcile_quotation(
            raw_data=parsed_json,
            document_text=document_text,
            source_file=source_file,
            source_pages=source_pages,
            metadata_extra={
                "extraction_engine": f"Gemma 4 ({model})",
                "model": model,
                "is_synthetic": False,
                "fallback_triggered": False,
            },
        )
        return quotation.to_contract_dict()

    except Exception as exc:
        logger.error(f"Gemma extraction failed: {exc}", exc_info=True)
        if allow_fallback:
            logger.warning("Extraction error encountered; triggering clearly-labelled mock fallback.")
            quotation = mock_extract_supplier_data(document_text, source_file, source_pages)
            quotation.metadata["fallback_triggered"] = True
            quotation.metadata["fallback_reason"] = str(exc)
            quotation.metadata["extraction_engine"] = "MOCK_FALLBACK (Model Failed/Unavailable)"
            return quotation.to_contract_dict()
        raise


def extract_supplier_data_model(
    document_text: str,
    source_file: str,
    source_pages: Optional[Union[int, List[int], Dict[int, str]]] = None,
    use_mock: bool = False,
    model: str = "gemma4:e2b",
    allow_fallback: bool = True,
) -> SupplierQuotation:
    """Convenience helper returning the SupplierQuotation Pydantic object."""
    data_dict = extract_supplier_data(
        document_text=document_text,
        source_file=source_file,
        source_pages=source_pages,
        use_mock=use_mock,
        model=model,
        allow_fallback=allow_fallback,
    )
    return SupplierQuotation.model_validate(data_dict)
