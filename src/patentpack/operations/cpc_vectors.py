from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional

from ..core.contracts import CountResult
from ..core.interfaces import PatentProvider, Which
from .cpc_codebook import Level, get_codebook


@dataclass(frozen=True)
class CPCVectorResult:
    company: str
    year: int
    level: Level  # 'section' | 'class' | 'subclass' | 'group'
    bins: Mapping[str, int]  # e.g. {'Y02': 772, 'H01': 423, ...}
    meta: Optional[Dict] = None


def _norm_codes(codes: Iterable[str]) -> List[str]:
    return [
        str(c).strip().upper().replace(" ", "")
        for c in codes
        if str(c).strip()
    ]


def _prefix_for_level(code: str, level: Level) -> str:
    """
    Normalize an arbitrary CPC symbol to the requested granularity.

    level:
      - 'section'   -> first letter, e.g. 'Y'
      - 'class'     -> letter+2 digits, e.g. 'Y02'
      - 'subclass'  -> class+letter, e.g. 'Y02C'
      - 'group'     -> subclass+2 digits (no slash), e.g. 'Y02C20'
    """
    code = (code or "").upper().replace(" ", "")
    if not code:
        return code
    if level == "section":
        return code[:1]
    if level == "class":
        return code[:3] if len(code) >= 3 else code
    if level == "subclass":
        return code[:4] if len(code) >= 4 else code
    if level == "group":
        import re

        # Accept 'Y02C20/00' or 'Y02C 20/00' -> 'Y02C20'
        m = re.match(r"^([A-HY]\d{2}[A-Z])\s*(\d{2})", code)
        return (m.group(1) + m.group(2)) if m else code
    return code


def cpc_class_vector(
    provider: PatentProvider,
    *,
    company: str,
    year: int,
    level: Level = "class",  # 'section' | 'class' | 'subclass' | 'group'
    codes: Iterable[str] | None = None,
    roots: Iterable[str] | None = None,  # optional filter when auto-loading
    which: Optional[Which] = None,
    utility_only: bool = False,
    keep_zeros: bool = True,
) -> CPCVectorResult:
    """
    Provider-agnostic CPC count vector for a single company-year.
    Uses provider.count_by_cpc_company_year under the hood.

    If `codes` is omitted, a codebook for the given `level` is auto-loaded
    (and cached) via PatentsView (shared CPC taxonomy). You can restrict that
    codebook with `roots` (e.g., roots=['Y02','H01']).

    Notes:
      - No name disambiguation here; pass exactly what your provider expects.
      - Group level codebook can be very large; consider roots=['Y02', ...].
    """
    lvl: str = str(level).strip().lower()
    if lvl not in ("section", "class", "subclass", "group"):
        raise ValueError(f"Unsupported CPC level: {level}")

    meta: Dict = {}

    # If explicit codes are not provided, load from codebook for this level
    if not codes:
        cb_codes, meta_cb = get_codebook(level=lvl, roots=roots)
        codes = cb_codes
        meta["codebook"] = meta_cb

    # Normalize → level-specific prefixes
    prefixes = [_prefix_for_level(c, lvl) for c in _norm_codes(codes)]

    out: Dict[str, int] = {}
    for pref in prefixes:
        if not pref:
            out[pref] = 0
            continue

        kwargs = dict(year=year, company=company, cpc=pref)
        if which is not None:
            kwargs["which"] = which
        if utility_only:
            kwargs["utility_only"] = True

        res: CountResult = provider.count_by_cpc_company_year(**kwargs)  # type: ignore[arg-type]
        out[pref] = int(res.total or 0)

    if not keep_zeros:
        out = {k: v for k, v in out.items() if v}

    meta.setdefault("provider", type(provider).__name__)
    meta.setdefault("prefixes", prefixes)

    return CPCVectorResult(
        company=company,
        year=year,
        level=lvl,
        bins=out,
        meta=meta,
    )
