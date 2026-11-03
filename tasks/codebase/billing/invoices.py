"""Invoice totals."""


def invoice_subtotal(lines):
    """lines is a list of (quantity, unit_price_cents). Returns the subtotal in cents."""
    return sum(quantity * price for quantity, price in lines)


def invoice_total(lines):
    """Total amount due for an invoice, in cents."""
    return invoice_subtotal(lines)
