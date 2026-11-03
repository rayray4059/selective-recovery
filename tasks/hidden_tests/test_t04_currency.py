import pytest

from billing.client import Client
from billing.errors import BillingError
from billing.payments import charge


def make_client():
    sent = []
    return Client("us-east", transport=lambda req: sent.append(req) or {"status": "ok"}), sent


@pytest.mark.parametrize("currency", ["USD", "EUR", "GBP"])
def test_supported_currencies(currency):
    client, sent = make_client()
    charge(client, 500, currency, idempotency_key="k1")
    assert sent[0]["currency"] == currency


@pytest.mark.parametrize("currency", ["JPY", "CAD"])
def test_other_currencies_rejected(currency):
    client, sent = make_client()
    with pytest.raises(BillingError) as err:
        charge(client, 500, currency, idempotency_key="k1")
    assert err.value.code == "unsupported_currency"
    assert sent == []
