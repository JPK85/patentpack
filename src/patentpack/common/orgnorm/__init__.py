from .core import (
    ADR_SUFFIX_RE,
    SPACE_RE,
    TRAILING_SLASH_TAG_RE,
    cmp_norm,
    name_has_ascii,
    norm,
    strip_adr_suffix,
)
from .country import (
    country_hints_from_name,
)
from .stem import (
    cmp_stem,
    is_adr_like_name,
)
from .variants import (
    expand_query_variants,
)

# Expose constants that other modules might need.
try:
    from .constants import (  # noqa: F401
        STOPWORDS,
        SUFFIX_COUNTRY_HINTS,
        SUFFIX_TO_FULL,
    )
except Exception:
    # constants.py may not be used everywhere; ignore if not present
    pass

__all__ = [
    # core
    "SPACE_RE",
    "TRAILING_SLASH_TAG_RE",
    "ADR_SUFFIX_RE",
    "norm",
    "strip_adr_suffix",
    "cmp_norm",
    "name_has_ascii",
    # stem
    "cmp_stem",
    "is_adr_like_name",
    # variants
    "expand_query_variants",
    # country
    "country_hints_from_name",
    # optional constants
    "STOPWORDS",
    "SUFFIX_TO_FULL",
    "SUFFIX_COUNTRY_HINTS",
]
