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


def _pv_post(path: str, *, page: int = 1, size: int = 1000) -> dict:
    url = f"{_PV_BASE}/{path.strip('/')}/"
    payload = {"q": {}, "o": {"page": page, "size": size}}
    r = requests.post(url, headers=_pv_headers(), json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def _pv_collect_ids(path: str, list_key: str, id_key: str) -> List[str]:
    # try to fetch everything with large pages; fall back to pagination for big lists
    size = 1000
    page = 1
    seen = []
    while True:
        data = _pv_post(path, page=page, size=size)
        rows = data.get(list_key) or []
        ids = [(row.get(id_key) or "").strip().upper() for row in rows if row.get(id_key)]
        if not ids:
            break
        seen.extend(ids)
        # progress
        print(f"[codebook] {path} page {page} • got={len(ids)} • total={len(seen)}")
        if len(ids) < size:
            break
        page += 1
        if page > 200:  # hard guard
            break
    return seen


def _fetch_codes(level: Level) -> Tuple[List[str], str]:
    if level == "section":
        return list("ABCDEFGHY"), "static"
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
        raw, src = _fetch_codes(level)
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
