from __future__ import annotations

from .constants import ADR_PAT, SPACE_RE, STOPWORDS, SUFFIX_RE
from .core import norm, strip_adr_suffix


def _strip_stopwords_from_tokens(tokens: list[str]) -> list[str]:
    return [t for t in tokens if t and t not in STOPWORDS]


def stem(s: str) -> str:
    """
    Normalized string with common corporate suffixes removed; keeps '&/and' canonicalization.
    """
    x = norm(s)
    x = SUFFIX_RE.sub("", x)
    x = SPACE_RE.sub(" ", x).strip()
    toks = _strip_stopwords_from_tokens(x.split())
    return " ".join(toks)


def cmp_stem(s: str) -> str:
    """Stemmed (suffix-stripped) string for comparisons (ADR suffix removed, corporate forms trimmed)."""
    # Strip ADR bits before stemming (stem() calls norm() again internally)
    return stem(strip_adr_suffix(s))


def is_adr_like_name(name: str) -> bool:
    return bool(ADR_PAT.search(name or ""))
