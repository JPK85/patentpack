from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

from .cache import CacheKey, NamePlanCache
from .discovery import discover_orgs_via_begins, eq_count
from .providers import get_provider
from .types import (
    Bucket,
    DiscoveryOptions,
    NamePlan,
    NamePlanResult,
    PlanOptions,
    VariantItem,
)
from .variants import build_bucketed_variants

# Stable print order for debug (subs before expansions if you prefer)
PRINT_ORDER: Dict[Bucket, int] = {
    "orig": 0,
    "gleif_legal": 1,
    "gleif_other": 2,
    "gleif_sub": 3,  # show subs earlier than expansions
    "expand_legal": 4,
    "expand_other": 5,
    "expand_orig": 6,
    "expand_sub": 7,
}


def plan_names(
    *,
    provider_name: str,
    year: int,
    base_name: str,
    gleif_legal: str = "",
    gleif_other_names: Iterable[str] = (),
    subsidiaries: Iterable[str] = (),
    plan_opts: Optional[PlanOptions] = None,
    probe_opts: Optional[DiscoveryOptions] = None,
    rpm: int = 30,
    cache: Optional[NamePlanCache] = None,
) -> NamePlanResult:
    """
    Public entry: build ordered variants; optionally run discovery and/or eq.

    Returns NamePlanResult with plan + (optional) discovery map + eq outcomes.
    """
    plan_opts = plan_opts or PlanOptions()
    # IMPORTANT: default = no probing, unless explicitly enabled
    probe_opts = probe_opts or DiscoveryOptions(
        run_discovery=False, run_eq=False
    )
    cache = cache or NamePlanCache()

    # 1) Build the variant list (agnostic)
    variants = build_bucketed_variants(
        base_name=base_name,
        gleif_legal=gleif_legal,
        gleif_other_names=list(gleif_other_names or []),
        subsidiaries=list(subsidiaries or []),
        include_expansions=plan_opts.include_expansions,
        max_variants=plan_opts.max_variants,
    )
    variants_sorted = sorted(
        variants, key=lambda v: PRINT_ORDER.get(v["bucket"], 99)
    )
    plan = NamePlan(
        ordered_variants=variants_sorted,
        counts_by_bucket=_count_by_bucket(variants_sorted),
    )

    # 2) If no probing requested, we’re done
    if not (probe_opts.run_discovery or probe_opts.run_eq):
        return NamePlanResult(plan=plan)

    provider = get_provider(provider_name, rpm=rpm)

    # We’ll compute discovery, eq_counts, trace, and best_* first,
    # THEN construct NamePlanResult exactly once.
    discovery: Dict[str, List[str]] = {}
    eq_counts: Dict[str, int] = {}
    trace: List[Dict] = []

    # 2a) discovery
    if probe_opts.run_discovery:
        for item in variants_sorted:
            seed = item["name"]
            k = CacheKey(
                provider=provider_name, year=year, op="discover", key=seed
            )
            cached = cache.get(k)
            if cached is not None:
                found = ["cached_hit"] if cached.get("has_hits", False) else []
            else:
                try:
                    found = discover_orgs_via_begins(
                        provider,
                        prefix=seed,
                        year=year,
                        limit=probe_opts.limit_discovery,
                    )
                except Exception:
                    found = []
                cache.put(k, {"has_hits": len(found) > 0})
            discovery[seed] = found
            trace.append(
                {
                    "op": "discover",
                    "seed": seed,
                    "bucket": item["bucket"],
                    "found_n": len(found),
                    "found_sample": found[:3],
                }
            )

    # 2b) eq (exact)
    best_total, best_variant, best_bucket = 0, "", ""
    if probe_opts.run_eq:
        names_to_eq: List[Tuple[str, str]] = []
        for item in variants_sorted:
            names_to_eq.append((item["name"], item["bucket"]))
            for d in discovery.get(item["name"], []):
                names_to_eq.append((d, item["bucket"]))

        for name, bucket in names_to_eq:
            k = CacheKey(provider=provider_name, year=year, op="eq", key=name)
            cached = cache.get(k)
            if cached is not None:
                if cached.get("has_hits", False):
                    cnt, payload = 1, {"cached": True}
                else:
                    cnt, payload = 0, {}
            else:
                try:
                    cnt, payload = eq_count(
                        provider,
                        company=name,
                        year=year,
                        utility_only=probe_opts.utility_only,
                    )
                except Exception:
                    cnt, payload = 0, {}
                cache.put(k, {"has_hits": cnt > 0})
            eq_counts[name] = cnt
            trace.append(
                {
                    "op": "eq",
                    "name": name,
                    "bucket": bucket,
                    "count": cnt,
                    "payload": payload,
                }
            )
            if cnt > best_total:
                best_total, best_variant, best_bucket = cnt, name, bucket

    # Construct the (frozen) result ONCE with final values.
    return NamePlanResult(
        plan=plan,
        discovery=discovery,
        eq_counts=eq_counts,
        best_variant=best_variant,
        best_bucket=best_bucket,
        best_total=best_total,
        trace=trace,
    )


def _count_by_bucket(items: List[VariantItem]) -> Dict[Bucket, int]:
    out: Dict[Bucket, int] = {
        "orig": 0,
        "gleif_legal": 0,
        "gleif_other": 0,
        "gleif_sub": 0,
        "expand_legal": 0,
        "expand_other": 0,
        "expand_orig": 0,
        "expand_sub": 0,
    }
    for it in items:
        out[it["bucket"]] = out.get(it["bucket"], 0) + 1
    return out
