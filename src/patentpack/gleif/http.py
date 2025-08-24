from __future__ import annotations

import sys
from typing import Any, Dict, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

GLEIF_API = "https://api.gleif.org/api/v1/lei-records"


def make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=6,
        backoff_factor=0.8,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update(
        {
            "Accept": "application/vnd.api+json",
            "User-Agent": "LUT-LBS-AI USPTO linker (contact: jaan-pauli.kimpimaki@lut.fi)",
        }
    )
    return s


def safe_get(
    session: requests.Session, params: Dict[str, Any]
) -> Tuple[Optional[Dict[str, Any]], int, str]:
    """
    Return (json_or_None, status_code, text_snippet). Never raises.
    """
    try:
        r = session.get(GLEIF_API, params=params, timeout=30)
        status = r.status_code
        text_snippet = (r.text or "")[:300].replace("\n", " ")
        if status >= 400:
            return (None, status, text_snippet)
        try:
            return (r.json(), status, text_snippet)
        except Exception:
            return (None, status, text_snippet)
    except Exception as e:
        return (None, -1, f"{type(e).__name__}: {e}")


def smoke_test(session: requests.Session) -> None:
    _, status, body = safe_get(session, {"page[size]": "1"})
    print(f"[smoke] GET {GLEIF_API} -> {status}", file=sys.stderr)
    if status >= 400:
        print(f"[smoke] body: {body}", file=sys.stderr)
