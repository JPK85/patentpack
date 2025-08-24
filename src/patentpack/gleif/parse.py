from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple


def as_legal_name(obj: Any) -> str:
    if isinstance(obj, dict):
        return str(obj.get("name", "") or "").strip()
    if isinstance(obj, str):
        return obj.strip()
    return ""


def as_other_names(arr: Any) -> List[str]:
    out: List[str] = []
    if isinstance(arr, list):
        for x in arr:
            if isinstance(x, dict):
                nm = x.get("name", "")
            else:
                nm = str(x)
            nm = (nm or "").strip()
            if nm:
                out.append(nm)
    return out


def extract_names(d: Dict) -> Tuple[str, List[str], str]:
    """
    Return (legal, other_names, hq_country) pulling from attributes. OR attributes.entity.
    """
    attr = d.get("attributes", {}) or {}
    ent = attr.get("entity", {}) or {}

    legal = as_legal_name(attr.get("legalName")) or as_legal_name(
        ent.get("legalName")
    )
    others = as_other_names(attr.get("otherNames")) or as_other_names(
        ent.get("otherNames")
    )
    hq = (
        attr.get("headquartersAddress") or ent.get("headquartersAddress") or {}
    ) or {}
    hq_country = (hq.get("country") or "").upper()
    return legal, others, hq_country


def pretty_first_record(rows: List[Dict]) -> str:
    if not rows:
        return "(no rows)"
    d = rows[0]
    attr = d.get("attributes", {}) or {}
    ent = attr.get("entity", {}) or {}
    sample = {
        "id": d.get("id"),
        "legalName": attr.get("legalName") or ent.get("legalName"),
        "otherNames": attr.get("otherNames") or ent.get("otherNames"),
        "hq": attr.get("headquartersAddress")
        or ent.get("headquartersAddress"),
    }
    return json.dumps(sample, ensure_ascii=False)[:600]
