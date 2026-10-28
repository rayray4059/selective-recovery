import pytest

from billing.client import Client
from billing.errors import BillingError, TransientError


def flaky_transport(failures):
    """Raise each error in `failures` in turn, then succeed. Records every call."""
    calls = []

    def transport(request):
        calls.append(request)
        if len(calls) <= len(failures):
            raise failures[len(calls) - 1]
        return {"status": "ok"}

    return transport, calls


def test_succeeds_after_two_transient_failures():
    transport, calls = flaky_transport([TransientError("blip"), TransientError("blip")])
    assert Client("us-east", transport=transport).send({"op": "ping"}) == {"status": "ok"}
    assert len(calls) == 3


def test_gives_up_after_three_attempts():
    transport, calls = flaky_transport([TransientError(f"blip{i}") for i in range(5)])
    with pytest.raises(TransientError) as err:
        Client("us-east", transport=transport).send({"op": "ping"})
    assert len(calls) == 3
    assert err.value.code == "blip2"


def test_other_errors_not_retried():
    transport, calls = flaky_transport([BillingError("card_declined")])
    with pytest.raises(BillingError) as err:
        Client("us-east", transport=transport).send({"op": "ping"})
    assert err.value.code == "card_declined" and len(calls) == 1
