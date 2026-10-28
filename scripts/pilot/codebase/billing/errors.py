"""Errors raised by the billing package."""


class BillingError(Exception):
    """A billing failure with a machine-readable code."""

    def __init__(self, code, message=""):
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code


class TransientError(BillingError):
    """A failure that may succeed if the request is sent again."""
