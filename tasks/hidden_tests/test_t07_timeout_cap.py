import pytest

from billing.config import load_config
from billing.errors import BillingError


def test_default_and_bounds_allowed():
    assert load_config()["timeout_s"] == 30
    assert load_config({"timeout_s": 1})["timeout_s"] == 1
    assert load_config({"timeout_s": 90})["timeout_s"] == 90
    assert load_config({"timeout_s": 120})["timeout_s"] == 120


@pytest.mark.parametrize("value", [0, 121, 600])
def test_out_of_range_rejected(value):
    with pytest.raises(BillingError) as err:
        load_config({"timeout_s": value})
    assert err.value.code == "invalid_timeout"


def test_unknown_key_still_rejected():
    with pytest.raises(KeyError):
        load_config({"timeout": 5})
