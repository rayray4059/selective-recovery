"""Billing settings: defaults merged with caller overrides."""

from billing.errors import BillingError

DEFAULTS = {
    "region": "us-east",
    "timeout_s": 30,
    "currency": "USD",
}


def load_config(overrides=None):
    """Return the defaults merged with any overrides. Unknown keys are an error."""
    config = dict(DEFAULTS)
    for key, value in (overrides or {}).items():
        if key not in DEFAULTS:
            raise KeyError(f"unknown config key: {key}")
        config[key] = value
    if not 1 <= config["timeout_s"] <= 120:
        raise BillingError("invalid_timeout", repr(config["timeout_s"]))
    return config
