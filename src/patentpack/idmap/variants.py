from __future__ import annotations

import re
from typing import Iterable, List, Literal, Optional, Tuple

from patentpack.common.orgnorm.variants import expand_query_variants  # type: ignore

from .cache import CacheKey, NamePlanCache
from .types import Bucket, VariantItem

_DESIGNATOR_TOKENS = {
    # EN / general
    "inc","incorporated","corp","corporation","co","company","ltd","limited",
    "plc","llc","lp","llp","l.p.","l.l.p","lllp","gmbh","ag","kg","kgaa","mbh",
    # FR/ES/PT/IT
    "sa","s.a.","sociedad anonima","sas","sasl","sasu","sarl","s.a.r.l","spa","s.p.a.","sapa","s.a.p.a",
    "srl","s.r.l","sl","s.l.","slu","s.l.u.","lda","l.da","ltda","limitada",
    # NL/BE/LU/DE/AT/CH
    "nv","bv","bvba","cv","cvba","se","verein","ag & co","ag&co",
    # Nordics
    "oy","oyj","ab","as","asa","a/s",
    # JP/KR/CN/TW/HK/SG
    "kk","kabushiki kaisha","kabushiki-gaisha","godo kaisha","g.k.","sdn bhd","pte ltd","private limited",
    "co ltd","co., ltd.","pte. ltd.","pteltd","co.,ltd.",
    # Others
    "pty ltd","proprietary limited","pty. ltd.","ptyltd","zrt","rt","oao","zao","ooo","ao","pa",
}

_DOT_RE = re.compile(r"\.")

def _normalize_token(tok: str) -> str:
    """Lower, strip outer punctuation, drop internal dots for matching."""
    t = tok.strip(" ,\"'()[]{}").lower()
    t = _DOT_RE.sub("", t)  # remove internal dots: 's.p.a.' -> 'spa'
    return t

def _has_designator(name: str) -> bool:
    toks = [_normalize_token(t) for t in (name or "").split()]
    return any(t in _DESIGNATOR_TOKENS for t in toks)

def _squash_ws(s: str) -> str:
    return " ".join(str(s or "").split()).strip()

def _add_uc_variant(name: str, bucket: Bucket, out: List[VariantItem], seen: set[str]) -> None:
    uc = _squash_ws((name or "").upper())
    if not uc:
        return
    if uc in seen:
        return
    # if original is already exactly the UC form, don't add a duplicate
    if uc == _squash_ws(name):
        # still mark seen so future calls won't add it
        seen.add(uc)
        return
    out.append(VariantItem(name=uc, bucket=bucket, kind="seed"))
    seen.add(uc)


def build_bucketed_variants(
    *,
    base_name: str,
    gleif_legal: str = "",
    gleif_other_names: Iterable[str] = (),
    subsidiaries: Iterable[str] = (),
    include_expansions: bool = True,
    max_variants: int = 0,
) -> List[VariantItem]:
    """
    Build ordered (name, bucket, kind) entries with pretty buckets:
      seeds first: orig → orig_uc → gleif_legal → gleif_other → gleif_sub
      then expansions: expand_legal → expand_other → expand_orig → expand_sub
      (UC of *expanded variants* are kept with their expand_* bucket)

    We keep original capitalization/punctuation for EQ sensitivity.
    """
    out: List[VariantItem] = []
    seen: set[str] = set()

    def push(
        name: str, bucket: Bucket, kind: Literal["seed", "expand"]
    ) -> None:
        nv = _squash_ws(name)
        if not nv or nv in seen:
            return
        seen.add(nv)
        out.append(VariantItem(name=nv, bucket=bucket, kind=kind))

    # ---------------- Seeds (ordered) ----------------
    if base_name:
        push(base_name, "orig", "seed")
        _add_uc_variant(base_name, "orig", out, seen)

    if gleif_legal:
        push(gleif_legal, "gleif_legal", "seed")
        _add_uc_variant(gleif_legal, "gleif_legal", out, seen)

    for nm in gleif_other_names or []:
        if nm:
            push(nm, "gleif_other", "seed")
            _add_uc_variant(nm, "gleif_other", out, seen)

    for sub in subsidiaries or []:
        if sub:
            push(sub, "gleif_sub", "seed")
            _add_uc_variant(sub, "gleif_sub", out, seen)

    # ---------------- Expansions ----------------
    if include_expansions:

        def expand_many(seed: str, bucket: Bucket) -> None:
            try:
                expanded = list(expand_query_variants(seed))
            except Exception:
                expanded = []

            for v in expanded:
                # keep only meaningful, distinct expansions with a designator
                if not v:
                    continue
                if _squash_ws(v) == _squash_ws(seed):
                    continue
                if not _has_designator(v):
                    continue

                # add expansion and its UC (UC stays in the same expand_* bucket)
                push(v, bucket, "expand")
                _add_uc_variant(v, bucket, out, seen)

            # NOTE: we intentionally do NOT add UC of the seed here.
            # Seeds (incl. UC) were already added above to keep all seeds
            # before any expansions.

        if gleif_legal:
            expand_many(_squash_ws(gleif_legal), "expand_legal")
        for nm in gleif_other_names or []:
            if nm:
                expand_many(_squash_ws(nm), "expand_other")
        if base_name:
            expand_many(_squash_ws(base_name), "expand_orig")
        for sub in subsidiaries or []:
            expand_many(_squash_ws(sub), "expand_sub")

    if max_variants and max_variants > 0:
        out = out[:max_variants]

    return out

def build_cache_aware_variants(
    *,
    base_name: str,
    gleif_legal: str = "",
    gleif_other_names: Iterable[str] = (),
    subsidiaries: Iterable[str] = (),
    include_expansions: bool = True,
    max_variants: int = 0,
    cache: Optional[NamePlanCache] = None,
    provider_name: str = "uspto",
    year: Optional[int] = None,
) -> List[VariantItem]:
    """
    Build variants with cache awareness - only generate variants for queries that haven't had hits.

    This function checks the cache first to see if the original variant has had any hits.
    If it has hits, it returns only those variants from the cache that have had hits.
    If no hits, it generates all variants as usual.
    """
    if cache is None:
        # Fall back to regular variant generation if no cache provided
        return build_bucketed_variants(
            base_name=base_name,
            gleif_legal=gleif_legal,
            gleif_other_names=gleif_other_names,
            subsidiaries=subsidiaries,
            include_expansions=include_expansions,
            max_variants=max_variants,
        )

    # Check if the original variant has had any hits
    orig_key = CacheKey(
        provider=provider_name, year=year or 0, op="discover", key=base_name
    )

    has_orig_hits = cache.has_hits(orig_key)

    if has_orig_hits:
        # If original has hits, only return variants that have had hits
        # For now, return just the original since we're simplifying the cache
        return [VariantItem(name=base_name, bucket="orig", kind="seed")]
    else:
        # No hits, generate all variants as usual
        return build_bucketed_variants(
            base_name=base_name,
            gleif_legal=gleif_legal,
            gleif_other_names=gleif_other_names,
            subsidiaries=subsidiaries,
            include_expansions=include_expansions,
            max_variants=max_variants,
        )
