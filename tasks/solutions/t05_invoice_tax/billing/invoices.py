"""Invoice totals."""

from decimal import ROUND_HALF_UP, Decimal


def invoice_subtotal(lines):
    """lines is a list of (quantity, unit_price_cents). Returns the subtotal in cents."""
    return sum(quantity * price for quantity, price in lines)


def invoice_total(lines):
    """Total amount due for an invoice, in cents."""
    subtotal = invoice_subtotal(lines)
    tax = (Decimal(subtotal) * Decimal("0.0825")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return subtotal + int(tax)
