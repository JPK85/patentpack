from __future__ import annotations

import json
import sys
import time
import xml.etree.ElementTree as ET
from typing import Dict, Optional

import requests
from requests.auth import HTTPBasicAuth

from ..config import (
    DEFAULT_RPM,
    DEFAULT_TIMEOUT_S,
    OPS_AUTH_URL,
    OPS_SEARCH_URL,
    epo_key,
    epo_secret,
)
from ..core.contracts import AssigneeList, CountResult
from ..core.interfaces import PatentProvider


def _extract_total_from_json(data: Dict) -> Optional[int]:
    try:
        return int(
            data["ops:world-patent-data"]["ops:biblio-search"][
                "@total-result-count"
            ]
        )
    except Exception:
        return None


def _extract_total_from_xml(xml_text: str) -> Optional[int]:
    try:
        ns = {"ops": "http://ops.epo.org"}
        root = ET.fromstring(xml_text)
        node = root.find(".//ops:biblio-search", ns)
        if node is None:
            return None
        val = node.attrib.get("total-result-count")
        return int(val) if val is not None else None
    except Exception:
        return None


def _ymd_bounds(year: int) -> tuple[str, str]:
    return f"{year:04d}0101", f"{year:04d}1231"


def _q_year_cpc(year: int, cpc_prefix: str) -> str:
    start, end = _ymd_bounds(year)
    return f'cpc=/low {cpc_prefix} and pd within "{start} {end}"'


def _q_company_year_cpc(company: str, year: int, cpc_prefix: str) -> str:
    start, end = _ymd_bounds(year)
    return f'applicant="{company}" and cpc=/low {cpc_prefix} and pd within "{start} {end}"'


class EpoProvider(PatentProvider):
    """
    EPO OPS implementation with lightweight debug.
    """

    def __init__(
        self,
        *,
        rpm: int = DEFAULT_RPM,
        key: Optional[str] = None,
        secret: Optional[str] = None,
        debug: bool = False,
    ) -> None:
        self._key = key or epo_key(required=True)
        self._secret = secret or epo_secret(required=True)
        self._session = requests.Session()
        self._timeout = DEFAULT_TIMEOUT_S
        self._token: Optional[str] = None
        self._token_exp: float = 0.0
        self._debug = bool(debug)
        self._set_rpm(rpm)

    # pacing -------------------------------------------------------------
    def _set_rpm(self, rpm: int) -> None:
        rpm = max(1, int(rpm))
        self._min_interval = 60.0 / rpm
        self._last_ts = 0.0

    def set_rpm(self, rpm: int) -> None:
        self._set_rpm(rpm)

    def _pace(self) -> None:
        now = time.monotonic()
        wait = self._min_interval - (now - self._last_ts)
        if wait > 0:
            time.sleep(wait)
        self._last_ts = time.monotonic()

    # auth ---------------------------------------------------------------
    def _get_token(self) -> str:
        # Reuse token if still valid
        if self._token and (time.time() + 60) < self._token_exp:
            return self._token
        r = requests.post(
            OPS_AUTH_URL,
            data={"grant_type": "client_credentials"},
            auth=HTTPBasicAuth(self._key, self._secret),
            headers={"Accept": "application/json"},
            timeout=self._timeout,
        )
        if self._debug:
            print(
                f"[OPS auth] status={r.status_code} ct={r.headers.get('Content-Type','')}",
                file=sys.stderr,
            )
            print(f"[OPS auth] body={r.text[:300]}", file=sys.stderr)
        r.raise_for_status()
        j = r.json()
        self._token = j["access_token"]
        self._token_exp = time.time() + int(j.get("expires_in", 1200))
        return self._token

    # low-level search ---------------------------------------------------
    def _search(self, query: str) -> requests.Response:
        self._pace()
        token = self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "X-OPS-Range": "1-1",  # only need total
        }
        r = self._session.get(
            OPS_SEARCH_URL,
            params={"q": query},
            headers=headers,
            timeout=self._timeout,
        )
        if self._debug:
            print(f"[OPS search] url={r.url}", file=sys.stderr)
            print(
                f"[OPS search] status={r.status_code} ct={r.headers.get('Content-Type','')}",
                file=sys.stderr,
            )
            print(f"[OPS search] body={r.text[:400]}", file=sys.stderr)
        return r

    def _count_for_query(self, query: str) -> int:
        r = self._search(query)
        if r.status_code == 404:
            return 0
        # If error codes arrive, show context in debug then raise
        if r.status_code >= 400:
            if self._debug:
                print(
                    f"[OPS search] error status={r.status_code} body={r.text[:400]}",
                    file=sys.stderr,
                )
            r.raise_for_status()

        ct = (r.headers.get("Content-Type") or "").lower()
        if "json" in ct:
            try:
                total = _extract_total_from_json(r.json())
            except Exception:
                total = None
            if total is not None:
                return total
            # some OPS endpoints return XML even with Accept: JSON
        # try XML fallback always
        total = _extract_total_from_xml(r.text)
        if total is not None:
            return total
        # If OPS responded with a fault XML, treat as zero
        if "<fault" in r.text.lower():
            return 0
        # Unknown shape: return 0 but keep debug
        if self._debug:
            print(
                "[OPS search] unknown response shape; treating as 0",
                file=sys.stderr,
            )
        return 0

    # PatentProvider methods --------------------------------------------
    def count_by_cpc_year(
        self,
        *,
        year: int,
        cpc: str,
        which: Optional[str] = None,
        utility_only: bool = False,
    ) -> CountResult:
        # which/utility_only don't map cleanly in OPS search; ignored here.
        query = _q_year_cpc(year=year, cpc_prefix=(cpc or "").upper())
        total = self._count_for_query(query)
        return CountResult(total=total)

    def count_by_cpc_company_year(
        self,
        *,
        year: int,
        cpc: str,
        company: str,
        which: Optional[str] = None,
        utility_only: bool = False,
    ) -> CountResult:
        query = _q_company_year_cpc(
            company=company, year=year, cpc_prefix=(cpc or "").upper()
        )
        total = self._count_for_query(query)
        return CountResult(total=total)

    def assignee_discover(
        self, *, prefix: str, limit: int = 400
    ) -> AssigneeList:
        raise NotImplementedError(
            "EPO assignee discovery is not supported via OPS search"
        )
