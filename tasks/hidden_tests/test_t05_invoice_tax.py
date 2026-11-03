from billing.invoices import invoice_subtotal, invoice_total


def test_tax_on_subtotal_not_per_line():
    assert invoice_total([(1, 101), (1, 101)]) == 219


def test_tax_rounds_half_up():
    assert invoice_total([(2, 100)]) == 217


def test_empty_invoice():
    assert invoice_total([]) == 0


def test_subtotal_unchanged():
    assert invoice_subtotal([(1, 101), (1, 101)]) == 202
