import pytest

from billing.client import Client
from billing.errors import BillingError
from billing.payments import charge


def make_client():
    sent = []
    return Client("us-east", transport=lambda req: sent.append(req) or {"status": "ok"}), sent


def test_small_charge_rejected():
    client, sent = make_client()
    with pytest.raises(BillingError) as err:
        charge(client, 49, "USD", idempotency_key="k1")
    assert err.value.code == "amount_too_small"
    assert sent == []


def test_minimum_charge_allowed():
    client, sent = make_client()
    charge(client, 50, "USD", idempotency_key="k1")
    assert len(sent) == 1


def test_zero_is_still_invalid_amount():
    client, _ = make_client()
    with pytest.raises(BillingError) as err:
        charge(client, 0, "USD", idempotency_key="k1")
    assert err.value.code == "invalid_amount"
