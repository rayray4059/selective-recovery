"""Fees added on top of charges and invoices."""

from decimal import ROUND_HALF_UP, Decimal


def service_fee(amount_cents):
    """Processing fee for a charge, in cents."""
    fee = (Decimal(amount_cents) * Decimal("0.029")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(fee) + 30


def late_fee(amount_cents, days_late):
    """Late fee in cents for a payment that is days_late days late."""
    periods = days_late // 30
    fee = (Decimal(amount_cents) * Decimal("0.015") * periods).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(fee)
