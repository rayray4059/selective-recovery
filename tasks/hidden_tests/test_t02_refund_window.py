import pytest

from billing.client import Client
from billing.errors import BillingError
from billing.payments import refund


def make_client():
    sent = []
    return Client("us-east", transport=lambda req: sent.append(req) or {"status": "ok"}), sent


def test_refund_inside_window():
    client, sent = make_client()
    refund(client, "ch_1", 500)
    refund(client, "ch_1", 500, days_since_charge=89)
    refund(client, "ch_1", 500, days_since_charge=90)
    assert len(sent) == 3


def test_refund_after_window_rejected():
    client, sent = make_client()
    with pytest.raises(BillingError) as err:
        refund(client, "ch_1", 500, days_since_charge=91)
    assert err.value.code == "refund_window_expired"
    assert sent == []


def test_invalid_amount_still_checked():
    client, _ = make_client()
    with pytest.raises(BillingError) as err:
        refund(client, "ch_1", 0)
    assert err.value.code == "invalid_amount"
