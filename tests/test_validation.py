"""
Tests for MAC address validation utility.
"""
import pytest

from src.api.utils.validators import is_valid_mac, validate_mac


@pytest.mark.parametrize("mac", [
    "AA:BB:CC:DD:EE:FF",
    "aa:bb:cc:dd:ee:ff",
    "00:1A:2B:3C:4D:5E",
    "FF:FF:FF:FF:FF:FF",
])
def test_valid_macs(mac: str):
    assert is_valid_mac(mac) is True


@pytest.mark.parametrize("mac", [
    "AA:BB:CC:DD:EE",          # too short
    "AA:BB:CC:DD:EE:FF:11",    # too long
    "GG:BB:CC:DD:EE:FF",       # invalid hex char
    "AABBCCDDEEFF",            # no colons
    "",
    "AA-BB-CC-DD-EE-FF",       # dashes instead of colons
])
def test_invalid_macs(mac: str):
    assert is_valid_mac(mac) is False


def test_validate_mac_raises_on_invalid():
    with pytest.raises(ValueError, match="MAC"):
        validate_mac("not-a-mac")


def test_validate_mac_returns_upper():
    result = validate_mac("aa:bb:cc:dd:ee:ff")
    assert result == "AA:BB:CC:DD:EE:FF"
