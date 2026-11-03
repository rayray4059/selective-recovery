from billing.payments import format_amount


def test_eur_uses_comma():
    assert format_amount(1999, "EUR") == "19,99 EUR"
    assert format_amount(5, "EUR") == "0,05 EUR"


def test_other_currencies_use_dot():
    assert format_amount(1999, "USD") == "19.99 USD"
    assert format_amount(1999, "GBP") == "19.99 GBP"
