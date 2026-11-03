from billing.fees import late_fee, service_fee


def test_no_fee_before_30_days():
    assert late_fee(10000, 0) == 0
    assert late_fee(10000, 29) == 0


def test_fee_per_full_30_days():
    assert late_fee(10000, 30) == 150
    assert late_fee(10000, 65) == 300


def test_rounds_half_up_and_returns_int():
    result = late_fee(300, 30)
    assert result == 5 and type(result) is int


def test_capped():
    assert late_fee(1000000, 90) == 2500


def test_service_fee_unchanged():
    assert service_fee(1000) == 59
