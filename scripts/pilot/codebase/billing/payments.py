"""Charges, refunds and amount helpers."""

from decimal import Decimal

from billing.errors import BillingError


def to_cents(amount):
    """Convert a dollar amount (str, int or Decimal) to cents."""
    return Decimal(str(amount)) * 100


def format_amount(amount_cents, currency):
    """Format cents for display, e.g. (1999, "USD") -> "19.99 USD"."""
    return f"{amount_cents // 100}.{amount_cents % 100:02d} {currency}"


def charge(client, amount_cents, currency):
    """Charge a customer and return the processor's response."""
    if not isinstance(amount_cents, int) or amount_cents <= 0:
        raise BillingError("invalid_amount", repr(amount_cents))
    return client.charge(amount_cents, currency)


def refund(client, charge_id, amount_cents):
    """Refund part or all of a charge."""
    if not isinstance(amount_cents, int) or amount_cents <= 0:
        raise BillingError("invalid_amount", repr(amount_cents))
    return client.refund(charge_id, amount_cents)
