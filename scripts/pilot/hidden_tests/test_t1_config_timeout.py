import pytest

from billing.config import load_config


def test_timeout_s_default_is_30():
    assert load_config()["timeout_s"] == 30


def test_timeout_s_override():
    assert load_config({"timeout_s": 5})["timeout_s"] == 5


def test_old_timeout_key_rejected():
    with pytest.raises(KeyError):
        load_config({"timeout": 5})
