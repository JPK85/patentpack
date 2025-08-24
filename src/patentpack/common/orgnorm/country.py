import re

from .constants import (
    SUFFIX_COUNTRY_HINTS,
)
from .core import norm


def country_hints_from_name(name: str) -> list[str]:
    """
    Return 2‑letter country hints when a short legal suffix is present (e.g., 'AG' → DE/AT/CH).
    """
    n = norm(name)
    toks = n.split()
    if not toks:
        return []
    last = toks[-1].replace(".", "")
    key = (
        "s.p.a."
        if re.fullmatch(r"s\.?\s*p\.?\s*a\.?|spa", last, flags=re.I)
        else last
    )
    return SUFFIX_COUNTRY_HINTS.get(key.lower(), [])
