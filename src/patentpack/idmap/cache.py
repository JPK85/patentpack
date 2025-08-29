from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ..config import CACHE_DIR

# Simplified cache that tracks whether queries have had any hits in harvest output.
# Keys are tuples (provider, year, op, key), where:
#   op  ∈ {"discover","eq"}
#   key is a seed (for discover) or a variant (for eq)
# Values:
#   discover -> {"has_hits": bool}  # True if any names were found in discovery
#   eq       -> {"has_hits": bool}  # True if count > 0
#
# NOTE: intentionally simple; upgrade to sqlite if/when needed.

_DEFAULT_PATH = Path(CACHE_DIR) / "idmap_cache.jsonl"
_LOCK = threading.Lock()


@dataclass(frozen=True)
class CacheKey:
    provider: str
    year: int
    op: str  # "discover" | "eq"
    key: str  # seed (discover) or variant (eq)


class NamePlanCache:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or _DEFAULT_PATH
        self._loaded = False
        self._mem: Dict[Tuple[str, int, str, str], Dict[str, Any]] = {}

    def _load(self) -> None:
        if self._loaded:
            return
        if not self.path.exists():
            self._loaded = True
            return
        with _LOCK:
            with self.path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        k = (
                            rec["provider"],
                            int(rec["year"]),
                            rec["op"],
                            rec["key"],
                        )
                        self._mem[k] = rec["val"]
                    except Exception:
                        continue
        self._loaded = True

    def get(self, k: CacheKey) -> Optional[Dict[str, Any]]:
        self._load()
        return self._mem.get((k.provider, k.year, k.op, k.key))

    def put(self, k: CacheKey, val: Dict[str, Any]) -> None:
        self._load()
        key_tuple = (k.provider, k.year, k.op, k.key)
        self._mem[key_tuple] = val
        rec = {
            "provider": k.provider,
            "year": k.year,
            "op": k.op,
            "key": k.key,
            "val": val,
        }
        with _LOCK:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def has_hits(self, k: CacheKey) -> bool:
        """Check if a query has had any hits (discovery or EQ)."""
        cached = self.get(k)
        if cached is None:
            return False
        return cached.get("has_hits", False)

    def mark_has_hits(self, k: CacheKey, has_hits: bool) -> None:
        """Mark whether a query has had hits — without clobbering other fields."""
        self._load()
        key_tuple = (k.provider, k.year, k.op, k.key)
        cur = self._mem.get(key_tuple, {})
        # Merge the flag into the existing value
        cur = {**cur, "has_hits": bool(has_hits)}
        self.put(k, cur)
