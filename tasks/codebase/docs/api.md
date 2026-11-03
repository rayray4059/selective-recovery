# Billing API reference

## Creating a client

`get_client(*, region, timeout_s=30, transport=None)`

- `region` is required and keyword-only. Valid regions are `"us-east"` and `"eu-west"`
  (`billing.client.REGIONS`). Any other value raises `BillingError("invalid_region")`.
- `transport` is a callable taking a request dict and returning a response dict. Tests pass
  a fake one.

`Client.charge(amount_cents, currency, idempotency_key=None)` and
`Client.refund(charge_id, amount_cents)` build a request and pass it to `Client.send`.

## Configuration keys

`load_config(overrides)` accepts these keys. Unknown keys raise `KeyError`.

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `region` | str | `"us-east"` | Default region for services that read config |
| `timeout_s` | int | `30` | Request timeout in seconds |
| `currency` | str | `"USD"` | Default currency |

## Charges

`payments.charge(client, amount_cents, currency, idempotency_key=None)`

- Every charge must carry a non-empty `idempotency_key`; otherwise raise
  `BillingError("missing_idempotency_key")` before contacting the processor.
- Zero, negative or non-integer amounts raise `BillingError("invalid_amount")`.

## Refunds

`payments.refund(client, charge_id, amount_cents, days_since_charge=0)` refunds part or all
of a charge. `days_since_charge` is how many days ago the charge was made.

## Retries

`Client.send` retries a request that fails with `TransientError`, at most 3 attempts in total.
Any other `BillingError` is raised immediately.
