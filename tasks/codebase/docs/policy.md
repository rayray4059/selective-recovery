# Billing policy

## Fees

- Late fee: 1.5% of the invoice amount for each full 30 days a payment is late, rounded half up
  to the cent. The late fee is capped at 2500 cents per invoice.
- The service fee on a charge is already implemented in `fees.service_fee`.

## Charges and refunds

- The minimum charge is 50 cents. Smaller positive amounts raise
  `BillingError("amount_too_small")`. Zero or negative amounts are still `invalid_amount`.
- Supported currencies are USD, EUR and GBP. Charging any other currency raises
  `BillingError("unsupported_currency")` before contacting the processor.
- Refunds are allowed up to 90 days after the charge (day 90 is still allowed). Later refunds
  raise `BillingError("refund_window_expired")` before contacting the processor.

## Regions

- The eu-west processor accepts only EUR and the us-east processor accepts only USD.
  `Client.charge` with any other currency for its region raises
  `BillingError("currency_region_mismatch")` without sending the request.

## Tax

- Sales tax is 8.25%, computed once on the invoice subtotal (not per line) and rounded half up
  to the cent. `invoice_total` returns the subtotal plus tax.

## Display

- EUR amounts are shown with a comma as the decimal separator, e.g. `19,99 EUR`. All other
  currencies use a dot, e.g. `19.99 USD`.

## Configuration

- `timeout_s` must be between 1 and 120 seconds inclusive. `load_config` raises
  `BillingError("invalid_timeout")` for any other value.

## Support

- Support hours are 9am-5pm Pacific, Monday to Friday.
- Billing disputes are handled by the finance team, not engineering.
