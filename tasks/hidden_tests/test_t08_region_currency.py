import pytest

from billing.client import Client
from billing.errors import BillingError


def make_client(region):
    sent = []
    return Client(region, transport=lambda req: sent.append(req) or {"status": "ok"}), sent


@pytest.mark.parametrize("region,currency", [("us-east", "USD"), ("eu-west", "EUR")])
def test_matching_currency_sent(region, currency):
    client, sent = make_client(region)
    client.charge(500, currency, idempotency_key="k1")
    assert len(sent) == 1


@pytest.mark.parametrize("region,currency", [("us-east", "EUR"), ("eu-west", "USD"), ("eu-west", "GBP")])
def test_mismatch_rejected(region, currency):
    client, sent = make_client(region)
    with pytest.raises(BillingError) as err:
        client.charge(500, currency, idempotency_key="k1")
    assert err.value.code == "currency_region_mismatch"
    assert sent == []


def test_refund_unchanged():
    client, sent = make_client("eu-west")
    client.refund("ch_1", 500)
    assert sent[0]["op"] == "refund"
