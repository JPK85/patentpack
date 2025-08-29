from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .providers import _post, _year_bounds


def _norm_words(s: str) -> str:
    """
    Normalize to lower + word boundaries (collapse non-alnum to single spaces).
    Ensures consistent tokenization for prefix/boundary matching.
    """
    if not s:
        return ""

    out: list[str] = []
    prev_space = False
    for ch in s:
        if ch.isalnum():
            out.append(ch.lower())
            prev_space = False
        else:
            if not prev_space:
                out.append(" ")
                prev_space = True

    # collapse any accidental double spaces
    return " ".join("".join(out).split()).strip()


def discover_orgs_via_begins(
    provider,
    *,
    prefix: str,
    year: int | None,
    limit: int = 60,
) -> List[str]:
    """
    Operator-first `_begins` discovery with a token-boundary guard:
      - pass the raw prefix to `_begins` (preserves case-sensitive hits),
      - keep any assignee whose RAW string startswith(raw_prefix)
        OR whose word-normalized form startswith(word_norm_prefix)
        with a boundary right after the prefix (end or space).
    """
    q_parts: List[dict] = []
    if year is not None:
        start, end = _year_bounds(provider, year)
        q_parts.extend(
            [{"_gte": {"patent_date": start}}, {"_lte": {"patent_date": end}}]
        )

    begins_clause = {"_begins": {"assignees.assignee_organization": prefix}}
    query = {"_and": q_parts + [begins_clause]} if q_parts else begins_clause

    payload = {
        "q": query,
        "f": ["assignees.assignee_organization"],
        "o": {"size": max(1, min(200, int(limit))), "page": 1},
    }
    data = _post(provider, payload)

    want_raw = (prefix or "").strip()
    want_words = _norm_words(prefix)

    out: List[str] = []
    seen: set[str] = set()
    for p in data.get("patents") or []:
        for a in p.get("assignees") or []:
            org = a.get("assignee_organization")
            if not isinstance(org, str) or not org:
                continue
            org_raw = org.strip()
            raw_ok = bool(want_raw) and org_raw.startswith(want_raw)
            ow = _norm_words(org_raw)
            if want_words:
                starts = ow.startswith(want_words)
                boundary_ok = starts and (
                    len(ow) == len(want_words) or ow[len(want_words)] == " "
                )
            else:
                boundary_ok = False

            if raw_ok or boundary_ok:
                if org_raw not in seen:
                    seen.add(org_raw)
                    out.append(org_raw)
    return out


def eq_count(
    provider,
    *,
    company: str,
    year: int,
    utility_only: bool = False,
) -> Tuple[int, Dict[str, Any]]:
    """
    Exact `_eq` on assignees.assignee_organization with year bounds.
    Returns (total_hits, payload) for audit/logging.
    """
    start, end = _year_bounds(provider, year)
    filters = [
        {"_gte": {"patent_date": start}},
        {"_lte": {"patent_date": end}},
        {"_eq": {"assignees.assignee_organization": company}},
    ]
    if utility_only:
        filters.append({"_eq": {"patent_type": "utility"}})
    payload = {"q": {"_and": filters}, "o": {"size": 0}}
    data = _post(provider, payload)
    return int(data.get("total_hits", 0)), payload
