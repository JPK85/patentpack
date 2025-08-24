from __future__ import annotations

from typing import Dict, List, Tuple

from patentpack.common.orgnorm import (
    SPACE_RE,
    cmp_norm,
    cmp_stem,
    is_adr_like_name,
    name_has_ascii,
)

from .parse import extract_names

# ---------- matching/ranking ----------
PRIORITY = {
    "exact_norm_legal": 4,  # strongest
    "exact_norm_other": 3,  # one of the variants hits an exact match
    "stem_eq_legal": 3,  # legal name stemmed matches target (low confidence)
    "token_set_eq_legal": 2,  # legal name token-set matches target (low c.)
    "token_set_eq_other": 1,  # one of the variants token-set matches (low c.)
}


def rule_for(target_name: str, legal: str, other_names: List[str]) -> str:
    # comparison-normalized (ADR suffix stripped; diacritics folded; '&' normalized; stopwords handled in stem)
    tn = cmp_norm(target_name)
    ts = cmp_stem(target_name)
    l_n = cmp_norm(legal)
    l_s = cmp_stem(legal)

    # --- dot-insensitive "exact" equality (handles Inc vs Inc., NV vs N.V., etc.) ---
    def undot(x: str) -> str:
        return x.replace(".", "")

    tn_u = undot(tn)
    l_n_u = undot(l_n)

    if (l_n == tn and l_n) or (l_n_u == tn_u and l_n_u):
        return "exact_norm_legal"

    for on in other_names:
        on_n = cmp_norm(on)
        if (on_n == tn and tn) or (undot(on_n) == tn_u and tn_u):
            return "exact_norm_other"

    # stem equality on legal (stopwords removed inside stem)
    if l_s == ts and ts:
        return "stem_eq_legal"

    # token-set equality (stopwords removed via stem())
    def toks(x: str) -> set[str]:
        return set(t for t in SPACE_RE.split(cmp_stem(x)) if t)

    t0 = toks(target_name)
    if t0 and toks(legal) == t0:
        return "token_set_eq_legal"
    for on in other_names:
        if t0 and toks(on) == t0:
            return "token_set_eq_other"

    return ""


def pick_top_matches(
    rows: List[Dict], target_name: str
) -> Tuple[List[Dict[str, str]], str, str]:
    """
    Return (matches, status, top_rule).
      - status: 'ok' (exactly 1 at top), 'ambiguous_multi' (>1 at top),
                'no_match', 'adr_only_candidates', or 'non_latin_only'.
    """
    had_candidates = bool(rows)
    any_adr = False
    any_ascii = False

    raw_cands: List[Tuple[str, Dict[str, str], bool]] = []

    for d in rows:
        lei = d.get("id") or (d.get("attributes", {}) or {}).get("lei") or ""
        legal, others, hq_country = extract_names(d)

        names_for_checks = [legal] + others
        if any(
            is_adr_like_name((n or "").lower()) for n in names_for_checks if n
        ):
            any_adr = True
        if any(name_has_ascii(n or "") for n in names_for_checks if n):
            any_ascii = True

        rule = rule_for(target_name, legal, others)
        if rule and lei:
            adr_like = any(
                is_adr_like_name((n or "").lower())
                for n in names_for_checks
                if n
            )
            raw_cands.append(
                (
                    rule,
                    {
                        "lei": lei,
                        "legal": legal,
                        "hq_country": hq_country,
                        "rule": rule,
                    },
                    adr_like,
                )
            )

    # prefer non-ADR
    cands = [c for c in raw_cands if not c[2]]
    if not cands:
        if had_candidates and any_adr:
            return ([], "adr_only_candidates", "")
        if had_candidates and not any_ascii:
            return ([], "non_latin_only", "")
        return ([], "no_match", "")

    top_score = max(PRIORITY.get(rule, 0) for rule, _, _ in cands)
    top = [c for c in cands if PRIORITY.get(c[0], 0) == top_score]
    top_d = [c[1] for c in top]

    if len(top_d) == 1:
        return (top_d, "ok", top_d[0]["rule"])
    else:
        return (top_d, "ambiguous_multi", top_d[0]["rule"])
