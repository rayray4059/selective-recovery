from decimal import Decimal

from billing.payments import to_cents


def test_returns_plain_int():
    result = to_cents("19.99")
    assert result == 1999 and type(result) is int
    assert type(to_cents(2)) is int and to_cents(2) == 200


def test_rounds_half_up():
    assert to_cents("0.005") == 1     # banker's rounding would give 0
    assert to_cents("0.125") == 13    # banker's rounding would give 12
    assert to_cents(Decimal("4.994")) == 499
