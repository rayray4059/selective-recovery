import pytest

from billing.client import get_client
from billing.errors import BillingError


def test_region_is_required():
    with pytest.raises(TypeError):
        get_client()


def test_region_is_keyword_only():
    with pytest.raises(TypeError):
        get_client("us-east")


def test_unknown_region_rejected_and_valid_ones_accepted():
    with pytest.raises(BillingError) as err:
        get_client(region="us")
    assert err.value.code == "invalid_region"
    assert get_client(region="eu-west").region == "eu-west"
