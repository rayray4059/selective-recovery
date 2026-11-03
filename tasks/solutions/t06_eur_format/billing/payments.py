"""Charges, refunds and amount helpers."""

from decimal import ROUND_HALF_UP, Decimal

from billing.errors import BillingError


def to_cents(amount):
    """Convert a dollar amount (str, int or Decimal) to cents."""
    cents = (Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(cents)


def format_amount(amount_cents, currency):
    """Format cents for display, e.g. (1999, "USD") -> "19.99 USD"."""
    sep = "," if currency == "EUR" else "."
    return f"{amount_cents // 100}{sep}{amount_cents % 100:02d} {currency}"


def charge(client, amount_cents, currency, idempotency_key=None):
    """Charge a customer and return the processor's response."""
    if not isinstance(amount_cents, int) or amount_cents <= 0:
        raise BillingError("invalid_amount", repr(amount_cents))
    if not idempotency_key:
        raise BillingError("missing_idempotency_key")
    return client.charge(amount_cents, currency, idempotency_key=idempotency_key)


def refund(client, charge_id, amount_cents, days_since_charge=0):
    """Refund part or all of a charge. days_since_charge is the age of the charge in days."""
    if not isinstance(amount_cents, int) or amount_cents <= 0:
        raise BillingError("invalid_amount", repr(amount_cents))
    return client.refund(charge_id, amount_cents)
