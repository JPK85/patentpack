"""
idmap
========
Provider-agnostic name variant planning and (optional) discovery/eq probing.
Caches *name-level* intelligence in JSONL under `CACHE_DIR` so downstream
modules (e.g., CPC vectors) can reuse it.

Depends on:
- patentpack.common.orgnorm.* for normalization & expansions
- patentpack.providers.factory for concrete provider sessions

This package ONLY concerns:
  - generating & ordering organization-name variants (seeds + expansions),
  - optionally probing a provider for discovery (_begins) and exact (_eq),
  - caching the *name* intelligence so other modules can reuse it.

Does not perform CPC or other analytics; it just plans and probes names.
"""

from .discovery import discover_orgs_via_begins, eq_count
from .runner import plan_names
from .types import (
    Bucket,
    DiscoveryOptions,
    NamePlan,
    NamePlanResult,
    PlanOptions,
    VariantItem,
)
from .variants import build_bucketed_variants

__all__ = [
    "Bucket",
    "VariantItem",
    "DiscoveryOptions",
    "PlanOptions",
    "NamePlan",
    "NamePlanResult",
    "build_bucketed_variants",
    "discover_orgs_via_begins",
    "eq_count",
    "plan_names",
]
