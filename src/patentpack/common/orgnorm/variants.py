from __future__ import annotations

import re
from typing import Callable, Iterable

from .constants import (
    DOTTING_MAP,
    SPACE_RE,
    SUFFIX_TO_FULL,
    TRAILING_SLASH_TAG_RE,
)

Transform = Callable[[str], Iterable[str]]

# ---- retrieval helpers ------------------------------------------------


def _run_pipeline(seeds: Iterable[str], steps: list[Transform]) -> list[str]:
    """
    Apply each transform sequentially over the growing set of strings.
    Equivalent to the old nested loops, but clearer and faster to read.
    We keep order stable and dedupe only at the very end of expand_query_variants.
    """
    current: list[str] = list(seeds)
    for step in steps:
        next_batch: list[str] = []
        for s in current:
            # Each step returns 1..N variants for a single input s
            for v in step(s):
                next_batch.append(v)
        current = next_batch
    return current


def _clean_base_for_variants(name: str) -> str:
    """
    Remove trailing ADR/ADS/GDR decorations and '/TAG' for retrieval variants.
    Note: ADR removal is done implicitly by norm() in most comparison paths;
    here we keep it lightweight and only drop the obvious tail & '/TAG' on raw.
    """
    s = (name or "").strip()
    s = TRAILING_SLASH_TAG_RE.sub("", s)
    s = re.sub(
        r"(?:\s*[-,]?\s*(?:adr(?:hedged)?|ads|gdr)(?:\s*\([^)]*\))?\s*)+$",
        "",
        s,
        flags=re.I,
    ).strip()
    return s


def _maybe_the_variants(original: str) -> list[str]:
    """
    If the name starts with 'The ' add a no-'The' variant; if it doesn’t, add a 'The ' variant.
    """
    out: list[str] = []
    s = (original or "").strip()
    if not s:
        return out
    if re.match(r"^\s*the\s+\S", s, flags=re.I):
        out.append(s)
        out.append(re.sub(r"^\s*the\s+", "", s, flags=re.I).strip())
    else:
        out.append(s)
        out.append(f"The {s}")
    seen, uniq = set(), []
    for v in out:
        if v not in seen:
            seen.add(v)
            uniq.append(v)
    return uniq


def _emit_both_dotted_and_undotted(
    seed: str, token: str, dotted: str
) -> list[str]:
    """
    Ensure dotted/undotted forms of a short legal token exist in the string.
    Works on whole-word tokens, case-insensitive.
    """
    out = [seed]
    pat_any = re.compile(
        r"\b"
        + re.escape(token)
        + r"\b|\b"
        + re.escape(dotted).replace(r"\.", r"\.?")
        + r"\b",
        re.I,
    )
    if pat_any.search(seed):
        undotted = pat_any.sub(token, seed)
        with_dots = pat_any.sub(dotted, seed)
        out.extend([undotted, with_dots])
    uniq, seen = [], set()
    for v in out:
        vv = re.sub(r"\.{2,}", ".", v)
        if vv not in seen:
            seen.add(vv)
            uniq.append(vv)
    return uniq


def _ensure_dotted_abbrev_variants(s: str) -> list[str]:
    out = [s]
    for undotted, dotted in DOTTING_MAP.items():
        out.extend(_emit_both_dotted_and_undotted(s, undotted, dotted))
    uniq, seen = [], set()
    for v in out:
        if v not in seen:
            seen.add(v)
            uniq.append(v)
    return uniq


def _canonical_italian_spa(s: str) -> list[str]:
    """
    Unified handler for Italian S.p.A. family & edge-cases like '& C SpA':
      - normalize any SPA-ish token to 'S.p.A.'
      - add a fully spelled variant 'Società per Azioni'
      - if pattern '& <LETTER> SpA' appears, add '& <LETTER>. S.p.A.' variant
    """
    out = [s]
    spa_pat = re.compile(r"(s\.?\s*p\.?\s*a\.?|spa)(\.)?\b", re.I)
    spelled_pat = re.compile(r"societ[aà]\s+per\s+azioni", re.I)

    if spa_pat.search(s) or spelled_pat.search(s):
        dotted = spa_pat.sub("S.p.A.", s)
        spelled = spa_pat.sub("Società per Azioni", s)
        out.extend([dotted, spelled])

    if spelled_pat.search(s):
        out.append(spelled_pat.sub("S.p.A.", s))

    pat_letter_spa = re.compile(
        r"(&\s*)([A-Za-z])(\.?\s+)(s\.?\s*p\.?\s*a\.?|spa)(\.)?\b", re.I
    )
    if pat_letter_spa.search(s):
        out.append(
            pat_letter_spa.sub(
                lambda m: f"{m.group(1)}{m.group(2).upper()}. S.p.A.", s
            )
        )

    seen, uniq = set(), []
    for v in out:
        if v not in seen:
            seen.add(v)
            uniq.append(v)
    return uniq


def _suffix_full_form_variant(s: str) -> list[str]:
    """
    If the name ends with a short suffix (AG/AB/NV/SA/SpA/…), add a variant with fully spelled form.
    """
    out = [s]
    toks = s.strip().split()
    if not toks:
        return out
    last = toks[-1].rstrip(".")
    map_key = (
        "s.p.a."
        if re.fullmatch(r"s\.?\s*p\.?\s*a\.?|spa", last, flags=re.I)
        else last.lower()
    )
    full = SUFFIX_TO_FULL.get(map_key)
    if full:
        out.append(" ".join(toks[:-1] + [full]))
    return list(dict.fromkeys(out))


def _swedish_ab_prefix_variants(s: str) -> list[str]:
    """
    If a name ends with AB/A.B./Aktiebolag(et), generate prefix variants:
      'SKF AB' -> 'AB SKF', 'Aktiebolaget SKF'
      'XYZ Aktiebolag' -> 'AB XYZ', 'Aktiebolaget XYZ'
    """
    out = [s]
    toks = s.strip().split()
    if not toks:
        return out
    last_raw = toks[-1]
    last_key = re.sub(r"[^a-z]", "", last_raw.lower())
    if last_key in {"ab", "a", "aktiebolag", "aktiebolaget"}:
        base = " ".join(toks[:-1]).strip()
        if base:
            out.extend([f"AB {base}", f"Aktiebolaget {base}"])
    return list(dict.fromkeys(out))


def _drop_trailing_single_token_suffix(s: str) -> list[str]:
    """
    Add a suffix-less variant for full-text retrieval. Conservative: only single-token forms are dropped.
    """
    out = [s]
    toks = s.strip().split()
    if not toks:
        return out
    last_raw = toks[-1]
    last_key = re.sub(r"[^a-z]", "", last_raw.lower())
    SINGLE = {
        "ab",
        "aktiebolag",
        "aktiebolaget",
        "ag",
        "nv",
        "bv",
        "sa",
        "spa",
        "oy",
        "oyj",
        "gmbh",
        "kk",
        "as",
        "asa",
        "se",
        "llc",
        "plc",
        "inc",
        "ltd",
        "kgaa",
        "kg",
        "sas",
        "srl",
        "aps",
        "pte",
        "pty",
    }
    if last_key in SINGLE and len(toks) >= 2:
        base = " ".join(toks[:-1]).strip()
        if base:
            out.append(base)
    return list(dict.fromkeys(out))


def _sanitize_query_value(s: str) -> str:
    """
    Light cleanup for values we send to APIs:
      - trim and collapse whitespace
      - collapse trailing multi-dots ('..' -> '.')
    """
    x = (s or "").strip()
    if not x:
        return ""
    x = SPACE_RE.sub(" ", x)
    x = re.sub(r"\.{2,}\s*$", ".", x)
    return x.strip()


# ---- public API -------------------------------------------------------


def expand_query_variants(name: str) -> list[str]:
    """
    Generate a compact set of *query* variants for retrieval:
      - remove obvious ADR tails and '/TAG'
      - optional leading 'The' variants
      - Co Ltd / Co., Ltd. → Company Limited
      - Italian SPA family normalization + spelled form
      - ensure dotted & undotted short-form tokens
      - add full written equivalents for AG/AB/NV/SA/…
      - Swedish AB prefix variants
      - drop single-token corporate suffix for fulltext
      - keep the original input first
      - sanitize (avoid 'S.p.A..', etc.)
    """
    base = _clean_base_for_variants(name)
    seeds = _maybe_the_variants(base) if base else []

    variants: list[str] = []

    def _co_ltd_to_company_limited(s: str) -> list[str]:
        v = re.sub(
            r"\bco\b\.?\s*,?\s*ltd\b\.?", "Company Limited", s, flags=re.I
        )
        # return both original and expanded if they differ, preserving order
        return [s] if v == s else [s, v]

    steps: list[Transform] = [
        _co_ltd_to_company_limited,
        _canonical_italian_spa,  # SPA dotted + spelled forms
        _suffix_full_form_variant,  # AG/AB/NV/SA → full form
        _ensure_dotted_abbrev_variants,  # BV<->B.V., NV<->N.V., SA<->S.A., etc.
        _swedish_ab_prefix_variants,  # 'SKF AB' -> 'AB SKF' / 'Aktiebolaget SKF'
        _drop_trailing_single_token_suffix,
    ]

    variants.extend(_run_pipeline(seeds, steps))

    seen = set()
    uniq: list[str] = []

    def push(val: str) -> None:
        cv = _sanitize_query_value(val)
        if cv and cv not in seen:
            seen.add(cv)
            uniq.append(cv)

    push((name or "").strip())
    for v in variants:
        push(v)

    return uniq
