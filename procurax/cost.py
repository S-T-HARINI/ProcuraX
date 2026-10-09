"""
Task 1: Landed-cost calculation engine for ProcuraX.

Calculates estimated procurement cost using available unit price, volume discounts,
transportation charges, and explicitly provided additional charges.
Guarantees:
- Distinguishes total cost from cost per unit.
- Preserves currency and forbids multi-currency merging without explicit rates.
- Flags missing cost inputs and never silently assumes missing is 0.
"""

from typing import Any, Dict, List, Optional, Union
from procurax.models import CostBreakdown, Supplier


def calculate_landed_cost(
    supplier: Union[Dict[str, Any], Supplier],
    quantity: int,
    additional_charges: float = 0.0,
    discount_pct: float = 0.0,
    target_currency: Optional[str] = None,
    currency_rates: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Calculate estimated procurement landed cost for a specific supplier and quantity.

    Args:
        supplier: Supplier dict or Supplier model following the shared contract.
        quantity: Order quantity (int).
        additional_charges: Explicit extra charges (handling, customs, taxes, etc.).
        discount_pct: Volume discount percentage (0-100).
        target_currency: If specified, target currency to convert to.
        currency_rates: Exchange rates mapping relative to target currency or base.
                        Example: {"USD_TO_INR": 83.0, "EUR_TO_INR": 90.0} or {"USD": 83.0, "INR": 1.0}

    Returns:
        Dict matching CostBreakdown schema with full transparency on completeness.
    """
    # Extract data from dict or model
    if isinstance(supplier, Supplier):
        s_data = supplier.model_dump()
    else:
        s_data = dict(supplier)

    supplier_id = s_data.get("supplier_id", "UNKNOWN")
    supplier_name = s_data.get("supplier_name", "Unknown Supplier")
    currency = s_data.get("currency")
    unit_price = s_data.get("unit_price")
    transport_cost = s_data.get("transport_cost")

    missing_cost_inputs: List[str] = []
    warnings: List[str] = []

    if unit_price is None:
        missing_cost_inputs.append("unit_price")
    elif unit_price < 0:
        raise ValueError(f"Negative unit price ({unit_price}) for supplier {supplier_id}")

    if transport_cost is None:
        missing_cost_inputs.append("transport_cost")
    elif transport_cost < 0:
        raise ValueError(f"Negative transport cost ({transport_cost}) for supplier {supplier_id}")

    if quantity < 0:
        raise ValueError(f"Quantity cannot be negative: {quantity}")

    # Currency verification and conversion
    effective_currency = currency or "INR"
    exchange_multiplier = 1.0

    if target_currency and target_currency != effective_currency:
        if not currency_rates:
            raise ValueError(
                f"Cannot convert from {effective_currency} to {target_currency} "
                f"without an explicit currency conversion rate."
            )
        # Check direct pair or rates mapping
        pair_key = f"{effective_currency}_TO_{target_currency}"
        if pair_key in currency_rates:
            exchange_multiplier = currency_rates[pair_key]
        elif effective_currency in currency_rates and target_currency in currency_rates:
            # e.g., rate to base
            exchange_multiplier = currency_rates[effective_currency] / currency_rates[target_currency]
        else:
            raise ValueError(
                f"Missing conversion rate for {effective_currency} to {target_currency}. "
                f"Provided rates: {list(currency_rates.keys())}"
            )
        effective_currency = target_currency

    if quantity == 0:
        return {
            "supplier_id": supplier_id,
            "supplier_name": supplier_name,
            "quantity": 0,
            "unit_price": unit_price,
            "base_cost": 0.0 if unit_price is not None else None,
            "transport_cost": 0.0,
            "additional_charges": 0.0,
            "discounts": 0.0,
            "total_landed_cost": 0.0 if not missing_cost_inputs else None,
            "cost_per_unit": None,
            "currency": effective_currency,
            "missing_cost_inputs": missing_cost_inputs,
            "is_complete": len(missing_cost_inputs) == 0,
            "warnings": warnings,
        }

    # If critical price is missing, do not assume zero!
    if "unit_price" in missing_cost_inputs:
        warnings.append(
            f"Cannot calculate landed cost for supplier {supplier_id}: unit_price is null/missing."
        )
        return {
            "supplier_id": supplier_id,
            "supplier_name": supplier_name,
            "quantity": quantity,
            "unit_price": None,
            "base_cost": None,
            "transport_cost": transport_cost * exchange_multiplier if transport_cost is not None else None,
            "additional_charges": additional_charges * exchange_multiplier,
            "discounts": 0.0,
            "total_landed_cost": None,
            "cost_per_unit": None,
            "currency": effective_currency,
            "missing_cost_inputs": missing_cost_inputs,
            "is_complete": False,
            "warnings": warnings,
        }

    # Base cost
    raw_base_cost = float(unit_price) * quantity
    discount_amount = raw_base_cost * (discount_pct / 100.0)
    discounted_base = raw_base_cost - discount_amount

    # Transport cost: if missing, flag it
    if "transport_cost" in missing_cost_inputs:
        warnings.append(
            f"transport_cost is missing for supplier {supplier_id}; landed cost may be incomplete."
        )
        total_landed_cost = None
        cost_per_unit = None
        is_complete = False
    else:
        raw_total = discounted_base + float(transport_cost) + float(additional_charges)
        total_landed_cost = round(raw_total * exchange_multiplier, 2)
        cost_per_unit = round(total_landed_cost / quantity, 4)
        is_complete = True

    return {
        "supplier_id": supplier_id,
        "supplier_name": supplier_name,
        "quantity": quantity,
        "unit_price": round(float(unit_price) * exchange_multiplier, 4),
        "base_cost": round(discounted_base * exchange_multiplier, 2),
        "transport_cost": round(float(transport_cost) * exchange_multiplier, 2) if transport_cost is not None else None,
        "additional_charges": round(float(additional_charges) * exchange_multiplier, 2),
        "discounts": round(discount_amount * exchange_multiplier, 2),
        "total_landed_cost": total_landed_cost,
        "cost_per_unit": cost_per_unit,
        "currency": effective_currency,
        "missing_cost_inputs": missing_cost_inputs,
        "is_complete": is_complete,
        "warnings": warnings,
    }
