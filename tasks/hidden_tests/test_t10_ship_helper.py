import billing
from billing.payments import is_supported_currency


def test_supported():
    assert all(is_supported_currency(c) for c in ("USD", "EUR", "GBP"))


def test_not_supported():
    assert not is_supported_currency("JPY")
    assert not is_supported_currency("")


def test_version_bumped():
    assert billing.__version__ == "1.5.0"
