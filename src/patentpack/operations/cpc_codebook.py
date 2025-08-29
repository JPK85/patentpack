from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Literal, Optional, Tuple

import requests

from ..config import CACHE_DIR, PATENTSEARCHKEY

Level = Literal["section", "class", "subclass", "group"]

_PV_BASE = "https://search.patentsview.org/api/v1"
# path, list_key, id_key
_ENDPOINTS = {
    "class": ("cpc_class", "cpc_classes", "cpc_class_id"),
    "subclass": ("cpc_subclass", "cpc_subclasses", "cpc_subclass_id"),
    "group": ("cpc_group", "cpc_groups", "cpc_group_id"),
}


def _cache_path(level: Level) -> Path:
    return CACHE_DIR / f"codebook_{level}.json"


def _pv_headers() -> dict:
    h = {"Accept": "application/json", "Content-Type": "application/json"}
    if PATENTSEARCHKEY:
        h["X-Api-Key"] = PATENTSEARCHKEY
    return h


def _pv_post(path: str, *, page: int = 1, size: int = 1000, q: Optional[dict] = None) -> dict:
    """
    Minimal POST wrapper.
    - For classifications, PatentsView expects {"q": {...}, "o": {"page": ..., "size": ...}}
    - `q` is optional (defaults to {}), used by group-per-subclass sweep.
    """
    url = f"{_PV_BASE}/{path.strip('/')}/"
    payload = {"q": (q or {}), "o": {"page": page, "size": size}}
    r = requests.post(url, headers=_pv_headers(), json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def _pv_collect_ids(path: str, list_key: str, id_key: str) -> List[str]:
    """
    Generic collector for endpoints that actually paginate correctly.
    Used for 'class' and 'subclass'.
    """
    size = 1000
    page = 1
    seen: List[str] = []
    seen_set = set()  # for progress sanity / de-dupe detection

    print(f"[codebook] {path} pagination start")
    while True:
        data = _pv_post(path, page=page, size=size)
        rows = data.get(list_key) or []
        ids = [(row.get(id_key) or "").strip().upper() for row in rows if row.get(id_key)]
        if not ids:
            print(f"[codebook] {path} page {page} • got=0 • stopping")
            break

        # progress & uniqueness
        before = len(seen_set)
        for v in ids:
            if v and v not in seen_set:
                seen_set.add(v)
                seen.append(v)
        after = len(seen_set)
        print(f"[codebook] {path} page {page} • got={len(ids)} • unique_total={after}")

        # stop conditions
        if len(ids) < size:
            print(f"[codebook] {path} page {page} • short page ({len(ids)}<{size}) • stopping")
            break
        if after == before:
            # page repeated same content (provider-side pagination bug)
            print(f"[codebook] {path} page {page} • no new ids • stopping")
            break

        page += 1
        if page > 200:  # hard guard: should never trigger for class/subclass
            print(f"[codebook] {path} page limit hit (200) • stopping")
            break

    return seen


def _collect_groups_via_subclasses(roots: Optional[Iterable[str]]) -> List[str]:
    """
    Robust collector for 'group' by sweeping per-subclass:
      POST /cpc_group/ with q={'cpc_subclass_id': <subclass>} and o={'size': 1000}
    This avoids broken multi-page behavior observed when trying to paginate cpc_group directly.
    """
    # Build/get the subclass codebook first
    from .cpc_codebook import get_codebook  # local import to avoid circulars at import time

    subclass_codes, meta = get_codebook("subclass")
    if roots:
        roots_u = [str(r).strip().upper() for r in roots if str(r).strip()]
        subclass_codes = [s for s in subclass_codes if any(s.startswith(r) for r in roots_u)]

    print(f"[codebook] group via subclasses • subclasses={len(subclass_codes)} (filtered)")
    size = 1000
    seen_set = set()
    seen: List[str] = []

    for idx, sc in enumerate(subclass_codes, start=1):
        data = _pv_post("cpc_group", page=1, size=size, q={"cpc_subclass_id": sc})
        rows = data.get("cpc_groups") or []
        ids = [(row.get("cpc_group_id") or "").strip().upper() for row in rows if row.get("cpc_group_id")]

        before = len(seen_set)
        for v in ids:
            if v and v not in seen_set:
                seen_set.add(v)
                seen.append(v)
        after = len(seen_set)

        # periodic progress
        added = after - before
        if added > 0 or (idx % 25 == 0):
            print(f"[codebook] group @{sc} ({idx}/{len(subclass_codes)}) • +{added} → groups={after}")

    return seen


def _fetch_codes(level: Level, roots: Optional[Iterable[str]] = None) -> Tuple[List[str], str]:
    """
    Fetch codes for the given level.
    - 'section': static A..H + Y
    - 'class'/'subclass': use endpoint pagination
    - 'group': sweep per-subclass (reliable), honoring optional `roots`
    """
    if level == "section":
        return list("ABCDEFGHY"), "static"

    if level == "group":
        # Explicit reason for not using _ENDPOINTS pagination here:
        # PatentsView's /cpc_group/ multi-page returns repeated first-page payloads
        # for us; to be deterministic we sweep per-subclass and aggregate.
        ids = _collect_groups_via_subclasses(roots)
        return ids, "pv"

    if level in _ENDPOINTS:
        path, list_key, id_key = _ENDPOINTS[level]
        ids = _pv_collect_ids(path, list_key, id_key)
        return ids, "pv"

    raise ValueError(f"Unknown level: {level}")


def get_codebook(
    level: Level, *, roots: Optional[Iterable[str]] = None
) -> Tuple[List[str], dict]:
    """
    Returns (codes, meta). Auto-caches under CACHE_DIR/codebook_{level}.json.
    If missing, fetches once from PatentsView (uses PATENTPACK_PV_KEY).
    `roots` optionally filters by prefixes (e.g., ["Y02","H01"]).
    """
    cache = _cache_path(level)
    if cache.exists():
        codes = json.loads(cache.read_text())
        meta = {
            "source": "cache",
            "path": str(cache),
            "level": level,
            "count": len(codes),
        }
        print(f"[codebook] cache hit: {cache} ({len(codes)} codes)")
    else:
        print(f"[codebook] cache miss: {cache}")
        print(f"[codebook] build start: level={level}")
        raw, src = _fetch_codes(level, roots=roots)
        codes = sorted(
            {
                str(c).strip().upper().replace(" ", "")
                for c in raw
                if isinstance(c, str) and c.strip()
            }
        )
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(codes, ensure_ascii=False))
        meta = {
            "source": src,
            "path": str(cache),
            "level": level,
            "count": len(codes),
        }
        print(f"[codebook] wrote cache: {cache} ({len(codes)} codes)")

    if roots:
        roots_u = [str(r).strip().upper() for r in roots if str(r).strip()]
        codes = [c for c in codes if any(c.startswith(r) for r in roots_u)]

    return codes, meta
