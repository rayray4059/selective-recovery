from billing.client import get_client
from billing.config import load_config
from billing.fees import service_fee
from billing.invoices import invoice_subtotal
from billing.payments import format_amount, to_cents


def test_to_cents():
    assert to_cents("19.99") == 1999
    assert to_cents("0.005") == 1


def test_format_amount():
    assert format_amount(1999, "USD") == "19.99 USD"


def test_service_fee():
    assert service_fee(1000) == 59


def test_invoice_subtotal():
    assert invoice_subtotal([(2, 150), (1, 99)]) == 399


def test_config_defaults():
    assert load_config()["timeout_s"] == 30


def test_get_client():
    assert get_client(region="eu-west").region == "eu-west"
