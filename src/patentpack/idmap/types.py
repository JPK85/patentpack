from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple, TypedDict

Bucket = Literal[
    "orig",
    "gleif_legal",
    "gleif_other",
    "gleif_sub",
    "expand_orig",
    "expand_legal",
    "expand_other",
    "expand_sub",
]


class VariantItem(TypedDict):
    name: str
    bucket: Bucket
    kind: Literal["seed", "expand"]  # purely informational for debugging


@dataclass(frozen=True)
class DiscoveryOptions:
    """Controls whether/how we talk to the provider."""

    run_discovery: bool = True
    run_eq: bool = False
    limit_discovery: int = 120
    utility_only: bool = False  # passed to eq_count only


@dataclass(frozen=True)
class PlanOptions:
    """
    Controls how we generate & order variants, independent of provider.
    """

    include_expansions: bool = True
    max_variants: int = 0  # 0 = uncapped (ordering preserved)


@dataclass(frozen=True)
class NamePlan:
    """
    The generated, ordered variant plan (agnostic of any outcomes).
    """

    ordered_variants: List[VariantItem] = field(default_factory=list)
    # bookkeeping for debugging/printing
    counts_by_bucket: Dict[Bucket, int] = field(default_factory=dict)

    def __post_init__(self):
        # auto-populate counts if variants provided; else leave {} (tests expect empty)
        if self.ordered_variants:
            counts: Dict[Bucket, int] = {}
            for it in self.ordered_variants:
                b = it["bucket"]  # type: ignore[index]
                counts[b] = counts.get(b, 0) + 1
            object.__setattr__(self, "counts_by_bucket", counts)


@dataclass(frozen=True)
class NamePlanResult:
    """
    Final result if discovery/eq was requested.
    """

    plan: NamePlan
    discovery: Dict[str, List[str]] = field(default_factory=dict)
    eq_counts: Dict[str, int] = field(default_factory=dict)
    best_variant: str = ""
    best_bucket: str = ""
    best_total: int = 0
    trace: List[Dict] = field(default_factory=list)
