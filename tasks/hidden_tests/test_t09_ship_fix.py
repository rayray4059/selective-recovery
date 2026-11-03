import billing
from billing.payments import format_amount


def test_negative_amounts():
    assert format_amount(-150, "USD") == "-1.50 USD"
    assert format_amount(-5, "USD") == "-0.05 USD"


def test_positive_amounts_unchanged():
    assert format_amount(1999, "USD") == "19.99 USD"
    assert format_amount(0, "USD") == "0.00 USD"


def test_version_bumped():
    assert billing.__version__ == "1.4.3"
