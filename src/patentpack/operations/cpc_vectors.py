from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional

from ..core.contracts import CountResult
from ..core.interfaces import PatentProvider, Which


@dataclass(frozen=True)
class CPCVectorResult:
    company: str
    year: int
    level: str  # 'section' | 'class' | 'subclass' | 'group'
    bins: Mapping[str, int]  # e.g. {'Y02': 772, 'H01': 423, ...}
    meta: Optional[Dict] = None


def _norm_codes(codes: Iterable[str]) -> List[str]:
    return [
        c.strip().upper().replace(" ", "") for c in codes if str(c).strip()
    ]


def _prefix_for_level(code: str, level: str) -> str:
    """
    Turn an arbitrary CPC symbol into a prefix at the requested granularity.
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
        # Accept 'Y02C20/00' or 'Y02C 20/00' -> 'Y02C20'
        import re

        m = re.match(r"^([A-HY]\d{2}[A-Z])\s*(\d{2})", code)
        return (m.group(1) + m.group(2)) if m else code
    # default: return as-is
    return code


def cpc_class_vector(
    provider: PatentProvider,
    *,
    company: str,
    year: int,
    level: str = "class",  # 'section' | 'class' | 'subclass' | 'group'
    codes: (
        Iterable[str] | None
    ) = None,  # e.g. ['Y02','H01'] — if None, you must pass something meaningful later
    which: Optional[
        Which
    ] = None,  # passed through to provider (ignored if unsupported)
    utility_only: bool = False,  # passed through to provider
    keep_zeros: bool = True,  # include zero bins in the result
) -> CPCVectorResult:
    """
    Provider-agnostic CPC count vector for a single company-year.
    Uses provider.count_by_cpc_company_year under the hood.

    You control granularity with `level` and by what `codes` you feed in.
    For example, for level='class', pass classes like ['Y02','H01','B60'].
    """
    if not codes:
        raise ValueError(
            "You must pass `codes` (an iterable of CPC codes to bin by)."
        )

    # normalize → level-specific prefixes
    prefixes = [_prefix_for_level(c, level) for c in _norm_codes(codes)]

    out: Dict[str, int] = {}
    for pref in prefixes:
        kwargs = dict(year=year, company=company, cpc=pref)  # type: ignore[call-arg]
        if which is not None:
            kwargs["which"] = which
        if utility_only:
            kwargs["utility_only"] = True

        res: CountResult = provider.count_by_cpc_company_year(**kwargs)  # type: ignore[arg-type]
        out[pref] = int(res.total or 0)

    # Optionally drop zeros (sometimes convenient for sparse vectors)
    if not keep_zeros:
        out = {k: v for k, v in out.items() if v}

    return CPCVectorResult(company=company, year=year, level=level, bins=out)
