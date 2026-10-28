import pytest

from billing.client import Client
from billing.errors import BillingError
from billing.payments import charge


def recording_client():
    sent = []
    client = Client("us-east", transport=lambda req: sent.append(req) or {"status": "ok"})
    return client, sent


@pytest.mark.parametrize("kwargs", [{}, {"idempotency_key": ""}])
def test_missing_key_rejected_before_sending(kwargs):
    client, sent = recording_client()
    with pytest.raises(BillingError) as err:
        charge(client, 500, "USD", **kwargs)
    assert err.value.code == "missing_idempotency_key"
    assert sent == []


def test_key_passed_to_processor():
    client, sent = recording_client()
    charge(client, 500, "USD", idempotency_key="order-42")
    assert len(sent) == 1 and sent[0]["idempotency_key"] == "order-42"
