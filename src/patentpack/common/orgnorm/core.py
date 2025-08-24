from __future__ import annotations

import html
import re
import unicodedata

from .constants import (
    ADR_SUFFIX_RE,
    ASCII_PAT,
    SPACE_RE,
    TRAILING_SLASH_TAG_RE,
)


# ---------- low-level helpers ----------
def _strip_accents(s: str) -> str:
    return "".join(
        ch
        for ch in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(ch)
    )


def _ampersand_to_and(s: str) -> str:
    # Canonicalize '&' ↔ 'and' for comparisons
    return re.sub(r"&", " and ", s)


# ---------- core normalizers ----------
def norm(s: str) -> str:
    """
    HTML-unescape, fold diacritics, normalize, canonicalize '&', lowercase,
    strip noise, collapse whitespace, drop trailing '/TAG' (limited set).
    Also collapse single-letter dots (e.g., 'C.' -> 'C'), and remove
    trailing periods from multi-letter tokens (e.g., 'co.' -> 'co').
    """
    if not isinstance(s, str):
        return ""
    x = s.strip()
    for _ in range(4):  # fix '&amp;amp;'
        new = html.unescape(x)
        if new == x:
            break
        x = new
    x = _strip_accents(x)
    x = unicodedata.normalize("NFKC", x)
    x = _ampersand_to_and(x)
    x = x.lower()

    # Drop very specific trailing slash tags like '/the', '/ny', '/de' (not 'A/B')
    x = TRAILING_SLASH_TAG_RE.sub("", x)

    # keep word chars, &, -, /, ., space
    x = re.sub(r"[^\w&\-/\. ]+", "", x)

    # collapse single-letter abbreviations like 'C.' -> 'C'
    x = re.sub(r"\b([a-z])\.(?=\s|$)", r"\1", x)

    # remove remaining trailing periods on tokens (e.g., 'co.' -> 'co', 'ltd.' -> 'ltd')
    x = re.sub(r"\.(?=\s|$)", "", x)

    return SPACE_RE.sub(" ", x).strip()


def strip_adr_suffix(s: str) -> str:
    """
    Remove trailing ADR/ADS/GDR decorations (incl. 'ADRhedged', '(ADR)', etc.) for comparison purposes.
    """
    x = s or ""
    x = norm(x)
    x = ADR_SUFFIX_RE.sub("", x).strip()
    return x


# ---------- comparison-normalized helpers ----------
def cmp_norm(s: str) -> str:
    """Normalized string for equality comparisons (ADR suffix removed)."""
    return strip_adr_suffix(s)


def name_has_ascii(name: str) -> bool:
    return bool(ASCII_PAT.search(name or ""))
