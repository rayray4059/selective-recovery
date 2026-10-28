"""Billing settings: defaults merged with caller overrides."""

DEFAULTS = {
    "region": "us-east",
    "timeout": 30,
    "currency": "USD",
}


def load_config(overrides=None):
    """Return the defaults merged with any overrides. Unknown keys are an error."""
    config = dict(DEFAULTS)
    for key, value in (overrides or {}).items():
        if key not in DEFAULTS:
            raise KeyError(f"unknown config key: {key}")
        config[key] = value
    return config
