from __future__ import annotations

import sys
from typing import Dict, List

from patentpack.common.orgnorm import (
    country_hints_from_name,
    expand_query_variants,
)

from .http import safe_get


def gleif_search_union(
    session,
    name: str,
    page_size: int = 200,
    debug: bool = False,
) -> List[Dict]:
    """
    Query multiple filters, union results, dedupe by LEI.

    IMPORTANT: Do NOT mix fulltext with other filters. Split requests into:
      A) entity.legalName=<variant>            (no country)
      B) entity.legalName=<variant> + country  (country hints only; no fulltext)
      C) fulltext=<variant>                    (no country)

    Name variants come from normalize.expand_query_variants(), which folds HTML
    entities/diacritics, canonicalizes '&'↔'and', handles 'C.'↔'C',
    expands legal forms (e.g., 'AG'↔'Aktiengesellschaft', 'SpA'↔'S.p.A.'),
    and drops trailing '/NY', '/DE', '/The', etc.
    """
    seen: set[str] = set()
    out: List[Dict] = []

    variants = expand_query_variants(name)
    country_hints = country_hints_from_name(name)

    if debug:
        print(f"[search] name='{name}'", file=sys.stderr)
        print(
            f"[search] variants ({len(variants)}): {variants}", file=sys.stderr
        )
        if country_hints:
            print(f"[search] country_hints: {country_hints}", file=sys.stderr)

    queries: List[dict] = []

    # A) exact legalName for each variant
    for v in variants:
        queries.append(
            {"filter[entity.legalName]": v, "page[size]": str(page_size)}
        )

    # B) legalName + country hints (limit to first 3 hints to cap request count)
    for v in variants:
        for cc in country_hints[:3]:
            queries.append(
                {
                    "filter[entity.legalName]": v,
                    "filter[entity.legalAddress.country]": cc,
                    "page[size]": str(page_size),
                }
            )

    # C) fulltext only (no other filters)
    for v in variants:
        queries.append({"filter[fulltext]": v, "page[size]": str(page_size)})

    # Execute and union-dedupe by LEI
    for q in queries:
        j, status, body = safe_get(session, q)
        if j is None:
            if debug:
                print(
                    f"[gleif] HTTP {status} for {q} | body: {body}",
                    file=sys.stderr,
                )
            continue
        data = j.get("data", []) or []
        for d in data:
            lei = d.get("id") or (d.get("attributes", {}) or {}).get("lei")
            if not lei or lei in seen:
                continue
            seen.add(lei)
            out.append(d)

    if debug:
        print(
            f"[search] union results: {len(out)} unique LEIs", file=sys.stderr
        )

    return out
