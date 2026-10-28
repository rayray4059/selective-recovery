"""Client for the payment processor."""

from billing.errors import BillingError, TransientError

REGIONS = ("us-east", "eu-west")


def _default_transport(request):
    """Stand-in for the network call; echoes the request back."""
    return {"status": "ok", "request": request}


class Client:
    def __init__(self, region, timeout_s=30, transport=None):
        self.region = region
        self.timeout_s = timeout_s
        self.transport = transport or _default_transport

    def send(self, request):
        """Send one request and return the processor's response."""
        return self.transport(dict(request, region=self.region, timeout_s=self.timeout_s))

    def charge(self, amount_cents, currency, idempotency_key=None):
        request = {"op": "charge", "amount_cents": amount_cents, "currency": currency}
        if idempotency_key is not None:
            request["idempotency_key"] = idempotency_key
        return self.send(request)

    def refund(self, charge_id, amount_cents):
        return self.send({"op": "refund", "charge_id": charge_id, "amount_cents": amount_cents})


def get_client(*, region, timeout_s=30, transport=None):
    """Return a client for the given region."""
    if region not in REGIONS:
        raise BillingError("invalid_region", repr(region))
    return Client(region, timeout_s=timeout_s, transport=transport)
