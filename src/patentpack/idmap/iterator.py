from __future__ import annotations

"""
iterator.py
-----------
Provider-backed resolution flow that remains name-focused and purpose-agnostic.

It:
  - accepts prebuilt candidates [(variant, bucket), ...]
  - resolves them against a NameProvider using the chosen strategy
  - yields a stream of NameEvent (EqAttemptResult | DiscoveryResult)
  - records discovery/eq results in NamePlanCache to avoid redundant calls later
  - never makes assumptions about "counts/CPC/summaries"; callers decide

Strategies:
  - "eq_then_discovery" (default):
      run exact on seeds (orig, gleif_legal, gleif_other, gleif_sub),
      if none hit, run discovery for (orig → gleif_legal → gleif_other → expand_*),
      firing eq on each harvested org immediately.
  - "discovery_first_for_seeds":
      for seeds in (orig, gleif_legal, gleif_other) run discovery, eq on finds, then
      fall back to exact eq on seeds that had no discovery results; finally do expand_* discovery.
"""

from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Protocol,
    Tuple,
    Union,
)

from .cache import CacheKey, NamePlanCache

# Diagnostic bucket ordering for plan printing and processing
SEED_BUCKETS = ["orig", "gleif_legal", "gleif_other", "gleif_sub"]
EXPAND_BUCKETS = ["expand_legal", "expand_other", "expand_orig", "expand_sub"]
ALL_BUCKETS = SEED_BUCKETS + EXPAND_BUCKETS


# --- Provider & event types (defined here; no .base import needed) ---


class NameProvider(Protocol):
    def count_eq(self, company: str, *, year: Optional[int]) -> int: ...

    def discover_prefix(
        self, prefix: str, *, year: Optional[int], limit: int
    ) -> List[str]: ...


@dataclass(frozen=True)
class EqAttemptResult:
    base_query: str
    year: Optional[int]
    variant: str
    bucket: str
    total: int
    meta: Dict[str, Any]


@dataclass(frozen=True)
class DiscoveryResult:
    base_query: str
    year: Optional[int]
    seed: str
    bucket: str
    harvested: List[str]
    meta: Dict[str, Any]


NameEvent = Union[EqAttemptResult, DiscoveryResult]


# --- lightweight cache adapter around NamePlanCache ---


class _Cache:
    def __init__(self, store: Optional[NamePlanCache] = None) -> None:
        self.store = store or NamePlanCache()

    @staticmethod
    def _year(y: Optional[int]) -> int:
        return int(y) if y is not None else 0

    def get_eq(
        self, provider_label: str, year: Optional[int], name: str
    ) -> Optional[int]:
        k = CacheKey(
            provider=provider_label, year=self._year(year), op="eq", key=name
        )
        if self.store.has_hits(k):
            # Return a placeholder count since we only track has_hits now
            return 1
        return None

    def put_eq(
        self, provider_label: str, year: Optional[int], name: str, count: int
    ) -> None:
        k = CacheKey(
            provider=provider_label, year=self._year(year), op="eq", key=name
        )
        self.store.mark_has_hits(k, count > 0)

    def get_discovery(
        self, provider_label: str, year: Optional[int], seed: str
    ) -> Optional[List[str]]:
        k = CacheKey(
            provider=provider_label,
            year=self._year(year),
            op="discover",
            key=seed,
        )
        if self.store.has_hits(k):
            # Return a placeholder list since we only track has_hits now
            return ["cached_hit"]
        return None

    def put_discovery(
        self,
        provider_label: str,
        year: Optional[int],
        seed: str,
        found: Iterable[str],
    ) -> None:
        k = CacheKey(
            provider=provider_label,
            year=self._year(year),
            op="discover",
            key=seed,
        )
        has_hits = len(list(found or [])) > 0
        self.store.mark_has_hits(k, has_hits)

    def has_hits(
        self, provider_label: str, year: Optional[int], op: str, key: str
    ) -> bool:
        """Check if a query has had any hits."""
        k = CacheKey(
            provider=provider_label, year=self._year(year), op=op, key=key
        )
        return self.store.has_hits(k)


@dataclass(frozen=True)
class ResolveConfig:
    strategy: str = "eq_then_discovery"
    discovery_limit: int = 120
    debug: bool = False


class NameResolver:
    def __init__(
        self,
        provider: NameProvider,
        cache: Optional[NamePlanCache] = None,
        provider_label: str = "provider",
    ) -> None:
        self.provider = provider
        self.cache = _Cache(cache)
        self.provider_label = provider_label  # for cache keys

    # ---------- Core public API ----------

    def resolve(
        self,
        *,
        base_query: str,
        year: Optional[int],
        candidates: List[Tuple[str, str]],
        strategy: str = "eq_then_discovery",
        discovery_limit: int = 120,
        debug: bool = False,
    ) -> Iterator[NameEvent]:
        """
        Yield NameEvent items describing everything we do (eq attempts + discoveries).
        No stopping logic beyond the chosen traversal strategy; downstream decides
        what to do with the stream.
        """
        cfg = ResolveConfig(
            strategy=strategy, discovery_limit=discovery_limit, debug=debug
        )

        # Plan print (debug only)
        if cfg.debug:
            print(
                f"[variants-plan] y={year or '-'} (N={len(candidates)})",
                flush=True,
            )
            prio = {b: i for i, b in enumerate(ALL_BUCKETS)}
            for v, b in sorted(candidates, key=lambda t: prio.get(t[1], 999)):
                print(f"    - [{b:<13}] {v}  ->  (queued)", flush=True)

        # Strategy dispatch
        if cfg.strategy == "eq_then_discovery":
            yield from self._resolve_eq_then_discovery(
                base_query, year, candidates, cfg
            )
        elif cfg.strategy == "discovery_first_for_seeds":
            yield from self._resolve_discovery_first_for_seeds(
                base_query, year, candidates, cfg
            )
        else:
            raise ValueError(f"Unknown strategy: {cfg.strategy}")

    # ---------- Strategies ----------

    def _resolve_eq_then_discovery(
        self,
        base_query: str,
        year: Optional[int],
        candidates: List[Tuple[str, str]],
        cfg: ResolveConfig,
    ) -> Iterator[NameEvent]:
        # Stage A: exact on *seeds only* (no expansions)
        for bucket in SEED_BUCKETS:
            for variant, b in candidates:
                if b != bucket:
                    continue
                cached = self.cache.get_eq(self.provider_label, year, variant)
                if cached is None:
                    total = self.provider.count_eq(variant, year=year)
                    self.cache.put_eq(
                        self.provider_label, year, variant, total
                    )
                else:
                    total = cached
                if cfg.debug:
                    print(
                        f"[eq] y={year or '-'} try={variant!r} bucket={b} -> total={total}",
                        flush=True,
                    )
                yield EqAttemptResult(
                    base_query=base_query,
                    year=year,
                    variant=variant,
                    bucket=b,
                    total=total,
                    meta={},
                )

        # Stage B: discovery (no subsidiaries)
        for bucket in [
            "orig",
            "gleif_legal",
            "gleif_other",
            "expand_legal",
            "expand_other",
            "expand_orig",
        ]:
            seeds = [v for (v, b) in candidates if b == bucket]
            for seed in seeds:
                cached_disc = self.cache.get_discovery(
                    self.provider_label, year, seed
                )
                if cached_disc is None:
                    harvested = self.provider.discover_prefix(
                        seed, year=year, limit=cfg.discovery_limit
                    )
                    self.cache.put_discovery(
                        self.provider_label, year, seed, harvested
                    )
                else:
                    harvested = cached_disc

                if cfg.debug:
                    sample = ", ".join(harvested[:3]) if harvested else "-"
                    print(
                        f"[discover] y={year or '-'} prefix={seed!r} bucket={bucket} -> harvested={len(harvested)} sample=[{sample}]",
                        flush=True,
                    )
                yield DiscoveryResult(
                    base_query=base_query,
                    year=year,
                    seed=seed,
                    bucket=bucket,
                    harvested=list(harvested),
                    meta={},
                )

                seen: set[str] = set()
                for org in harvested:
                    if org in seen:
                        continue
                    seen.add(org)
                    cached_eq = self.cache.get_eq(
                        self.provider_label, year, org
                    )
                    if cached_eq is None:
                        total = self.provider.count_eq(org, year=year)
                        self.cache.put_eq(
                            self.provider_label, year, org, total
                        )
                    else:
                        total = cached_eq
                    if cfg.debug:
                        print(
                            f"[eq] y={year or '-'} try={org!r} bucket={bucket} -> total={total}",
                            flush=True,
                        )
                    yield EqAttemptResult(
                        base_query=base_query,
                        year=year,
                        variant=org,
                        bucket=bucket,
                        total=total,
                        meta={},
                    )

    def _resolve_discovery_first_for_seeds(
        self,
        base_query: str,
        year: Optional[int],
        candidates: List[Tuple[str, str]],
        cfg: ResolveConfig,
    ) -> Iterator[NameEvent]:
        # Stage A: discovery for seeds
        for bucket in ["orig", "gleif_legal", "gleif_other"]:
            seeds = [v for (v, b) in candidates if b == bucket]
            for seed in seeds:
                cached_disc = self.cache.get_discovery(
                    self.provider_label, year, seed
                )
                if cached_disc is None:
                    harvested = self.provider.discover_prefix(
                        seed, year=year, limit=cfg.discovery_limit
                    )
                    self.cache.put_discovery(
                        self.provider_label, year, seed, harvested
                    )
                else:
                    harvested = cached_disc

                if cfg.debug:
                    sample = ", ".join(harvested[:3]) if harvested else "-"
                    print(
                        f"[discover] y={year or '-'} prefix={seed!r} bucket={bucket} -> harvested={len(harvested)} sample=[{sample}]",
                        flush=True,
                    )
                yield DiscoveryResult(
                    base_query=base_query,
                    year=year,
                    seed=seed,
                    bucket=bucket,
                    harvested=list(harvested),
                    meta={},
                )

                # eq on harvested first
                seen: set[str] = set()
                for org in harvested:
                    if org in seen:
                        continue
                    seen.add(org)
                    cached_eq = self.cache.get_eq(
                        self.provider_label, year, org
                    )
                    if cached_eq is None:
                        total = self.provider.count_eq(org, year=year)
                        self.cache.put_eq(
                            self.provider_label, year, org, total
                        )
                    else:
                        total = cached_eq
                    if cfg.debug:
                        print(
                            f"[eq] y={year or '-'} try={org!r} bucket={bucket} -> total={total}",
                            flush=True,
                        )
                    yield EqAttemptResult(
                        base_query=base_query,
                        year=year,
                        variant=org,
                        bucket=bucket,
                        total=total,
                        meta={},
                    )

            # now eq each seed that had zero discovery knowledge
            for seed in seeds:
                cached_disc = self.cache.get_discovery(
                    self.provider_label, year, seed
                )
                had_none = cached_disc is None or len(cached_disc) == 0
                if had_none:
                    cached_eq = self.cache.get_eq(
                        self.provider_label, year, seed
                    )
                    if cached_eq is None:
                        total = self.provider.count_eq(seed, year=year)
                        self.cache.put_eq(
                            self.provider_label, year, seed, total
                        )
                    else:
                        total = cached_eq
                    if cfg.debug:
                        print(
                            f"[eq] y={year or '-'} try={seed!r} bucket={bucket} -> total={total}",
                            flush=True,
                        )
                    yield EqAttemptResult(
                        base_query=base_query,
                        year=year,
                        variant=seed,
                        bucket=bucket,
                        total=total,
                        meta={},
                    )

        # Stage B: discovery on expansions
        for bucket in ["expand_legal", "expand_other", "expand_orig"]:
            seeds = [v for (v, b) in candidates if b == bucket]
            for seed in seeds:
                cached_disc = self.cache.get_discovery(
                    self.provider_label, year, seed
                )
                if cached_disc is None:
                    harvested = self.provider.discover_prefix(
                        seed, year=year, limit=cfg.discovery_limit
                    )
                    self.cache.put_discovery(
                        self.provider_label, year, seed, harvested
                    )
                else:
                    harvested = cached_disc

                if cfg.debug:
                    sample = ", ".join(harvested[:3]) if harvested else "-"
                    print(
                        f"[discover] y={year or '-'} prefix={seed!r} bucket={bucket} -> harvested={len(harvested)} sample=[{sample}]",
                        flush=True,
                    )
                yield DiscoveryResult(
                    base_query=base_query,
                    year=year,
                    seed=seed,
                    bucket=bucket,
                    harvested=list(harvested),
                    meta={},
                )

                seen: set[str] = set()
                for org in harvested:
                    if org in seen:
                        continue
                    seen.add(org)
                    cached_eq = self.cache.get_eq(
                        self.provider_label, year, org
                    )
                    if cached_eq is None:
                        total = self.provider.count_eq(org, year=year)
                        self.cache.put_eq(
                            self.provider_label, year, org, total
                        )
                    else:
                        total = cached_eq
                    if cfg.debug:
                        print(
                            f"[eq] y={year or '-'} try={org!r} bucket={bucket} -> total={total}",
                            flush=True,
                        )
                    yield EqAttemptResult(
                        base_query=base_query,
                        year=year,
                        variant=org,
                        bucket=bucket,
                        total=total,
                        meta={},
                    )
