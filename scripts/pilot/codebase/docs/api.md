# Billing API reference

## Creating a client

`get_client(*, region, timeout_s=30, transport=None)`

- `region` is **required and keyword-only**. There is no default region; calling
  `get_client()` without one is an error (a `TypeError`, as Python raises for a missing
  keyword-only argument).
- Valid regions are `"us-east"` and `"eu-west"` (`billing.client.REGIONS`). Any other value
  raises `BillingError` with code `"invalid_region"`.
- `transport` is a callable taking a request dict and returning a response dict. Tests pass
  a fake one.

## Configuration keys

`load_config(overrides)` accepts these keys. Unknown keys raise `KeyError`.

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `region` | str | `"us-east"` | Default region for services that read config |
| `timeout_s` | int | `30` | Request timeout in seconds |
| `currency` | str | `"USD"` | Default currency |

The old key `timeout` was renamed to `timeout_s` and is no longer accepted.

## Charges

`payments.charge(client, amount_cents, currency, idempotency_key)`

- Every charge **must** carry a non-empty `idempotency_key` string. The processor uses it to
  drop duplicate charges when a request is resent.
- If the key is missing or empty, raise `BillingError` with code
  `"missing_idempotency_key"` before contacting the processor.
- Pass the key through to `Client.charge(..., idempotency_key=...)`.

## Refunds

`payments.refund(client, charge_id, amount_cents)` refunds part or all of a charge.
Refunds do not take an idempotency key.

## Retries

`Client.send` retries a request that fails with `TransientError`.

- At most **3 attempts in total** (the first try plus 2 retries). No delay between attempts.
- Any other `BillingError` is raised immediately and not retried.
- If all 3 attempts fail, raise the last `TransientError`.
