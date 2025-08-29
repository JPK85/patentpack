from __future__ import annotations

from typing import List


def _gleif_subsidiaries_for_lei(subs_df, parent_lei: str) -> List[str]:
    # Lazy import so pandas isn't a hard dependency of patentpack
    try:
        import pandas as pd  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "pandas is required for _gleif_subsidiaries_for_lei"
        ) from e

    if subs_df is None:
        return []
    if not hasattr(subs_df, "empty") or subs_df.empty:
        return []
    key = str(parent_lei).strip().upper()
    rows = subs_df[subs_df["parent_lei"].astype(str).str.upper() == key]
    out: List[str] = []
    seen: set[str] = set()
    for nm in rows.get("subsidiary_name", []):
        v = " ".join(str(nm).split()).strip()
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _score_sub_name(nm: str, brand_hint: str) -> float:
    n = (nm or "").lower()
    score = 0.0
    if any(
        t in n
        for t in [
            "gmbh",
            "inc",
            "ltd",
            "llc",
            "plc",
            "co.",
            "co ",
            "s.a.",
            "s.p.a",
            "k.k.",
            "kabushiki kaisha",
        ]
    ):
        score += 1.0
    if any(
        t in n
        for t in [
            "manufactur",
            "technology",
            "tech",
            "electronics",
            "chemical",
            "materials",
            "optical",
            "semiconductor",
            "software",
            "systems",
        ]
    ):
        score += 0.5
    if any(
        t in n
        for t in [
            "holdings",
            "investment",
            "capital",
            "finance",
            "group",
            "holdco",
            "treasury",
        ]
    ):
        score -= 0.75
    if brand_hint and brand_hint.lower() in n:
        score += 0.5
    return score
