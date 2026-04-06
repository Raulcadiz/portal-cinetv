"""Reusable validation helpers used across all portal endpoints."""
import re

# Matches XX:XX:XX:XX:XX:XX where X is a hex digit (upper or lower case)
_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


def is_valid_mac(mac: str) -> bool:
    """Return ``True`` if *mac* is a valid IEEE 802 MAC address (XX:XX:XX:XX:XX:XX)."""
    return bool(_MAC_RE.match(mac))


def validate_mac(mac: str) -> str:
    """
    Validate and normalise a MAC address to uppercase.

    Raises :class:`ValueError` if the format is invalid.
    Used as a Pydantic field validator.
    """
    if not is_valid_mac(mac):
        raise ValueError(
            f"Invalid MAC address '{mac}'. Expected format: XX:XX:XX:XX:XX:XX "
            f"(hex digits separated by colons)."
        )
    return mac.upper()
