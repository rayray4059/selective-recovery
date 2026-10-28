# Billing conventions

## Money

- All amounts are **integer cents** (`int`). Never store or return money as `float` or `Decimal`.
- To convert dollars to cents, parse with `Decimal`, multiply by 100 and round to a whole
  cent with **`ROUND_HALF_UP`** (so half a cent rounds up). Return an `int`.

## Errors

- Raise `billing.errors.BillingError` with a short snake_case `code`, e.g.
  `BillingError("invalid_amount")`. Don't return `None` or `False` to signal failure.
- `TransientError` (a subclass) marks failures that may succeed if retried.

## Currency

- Currencies are three-letter uppercase ISO codes such as `"USD"` or `"EUR"`.

## Style

- Public functions have a one-line docstring. Keep modules dependency-free (standard
  library only).
