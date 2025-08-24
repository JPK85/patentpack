from __future__ import annotations

import json
import sys
import time
from typing import Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import (
    DEFAULT_RPM,
    DEFAULT_TIMEOUT_S,
    PATENTSEARCH_API_URL,
    PATENTSEARCHKEY,
    RETRY_ALLOWED_METHODS,
    RETRY_BACKOFF_FACTOR,
    RETRY_STATUS_FORCELIST,
)
from ..core.contracts import Assignee, AssigneeList, CountResult
from ..core.interfaces import PatentProvider, Which


class UsptoProvider(PatentProvider):
    """
    PatentSearch (PatentsView) provider implementation.

    Endpoints:
      POST {PATENTSEARCH_API_URL}   # e.g., https://search.patentsview.org/api/v1/patent/

    Notes:
      - API key is REQUIRED via X-Api-Key.
      - Use nested field paths for filters (e.g., assignees.assignee_organization).
      - Use `total_hits` from the response for counts.
    """

    def __init__(
        self,
        *,
        rpm: int = DEFAULT_RPM,
        api_key: Optional[str] = None,
        debug: bool = False,
    ) -> None:
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        key = api_key or PATENTSEARCHKEY
        if not key:
            raise RuntimeError(
                "PATENTPACK_PV_KEY is required (X-Api-Key for PatentSearch). "
                "Set env var PATENTPACK_PV_KEY or pass api_key=..."
            )
        self._session.headers["X-Api-Key"] = key

        retry = Retry(
            total=6,
            backoff_factor=RETRY_BACKOFF_FACTOR,
            status_forcelist=RETRY_STATUS_FORCELIST,
            allowed_methods=RETRY_ALLOWED_METHODS,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

        self._timeout = DEFAULT_TIMEOUT_S
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

    # helpers ------------------------------------------------------------
    @staticmethod
    def _year_bounds(year: int) -> tuple[str, str]:
        return f"{year:04d}-01-01", f"{year:04d}-12-31"

    def _post(self, payload: Dict) -> Dict:
        self._pace()
        r = self._session.post(
            PATENTSEARCH_API_URL, json=payload, timeout=self._timeout
        )
        if self._debug:
            print(
                f"[USPTO POST] url={r.request.url} status={r.status_code}",
                file=sys.stderr,
            )
            print(
                f"[USPTO POST] payload={json.dumps(payload)[:400]}",
                file=sys.stderr,
            )
            print(f"[USPTO POST] body={r.text[:400]}", file=sys.stderr)
        r.raise_for_status()
        return r.json()

    # PatentProvider methods --------------------------------------------
    def count_by_cpc_year(
        self,
        *,
        year: int,
        cpc: str,
        which: Optional[Which] = "cpc_current",
        utility_only: bool = False,
    ) -> CountResult:
        start, end = self._year_bounds(year)
        cpc_prefix = (cpc or "").upper()
        cpc_field = (
            "cpc_current.cpc_subclass"
            if which != "cpc_at_issue"
            else "cpc_at_issue.cpc_subclass"
        )

        filters: List[Dict] = [
            {"_gte": {"patent_date": start}},
            {"_lte": {"patent_date": end}},
            {"_begins": {cpc_field: cpc_prefix}},
        ]
        if utility_only:
            filters.append({"patent_type": "utility"})

        payload = {
            "q": {"_and": filters},
            # We only need the count; a size of 1 is enough.
            "o": {"size": 1},
        }
        data = self._post(payload)
        total = int(data.get("total_hits", 0))
        return CountResult(total=total)

    def count_by_cpc_company_year(
        self,
        *,
        year: int,
        cpc: str,
        company: str,
        which: Optional[Which] = "cpc_current",
        utility_only: bool = False,
    ) -> CountResult:
        start, end = self._year_bounds(year)
        cpc_prefix = (cpc or "").upper()
        cpc_field = (
            "cpc_current.cpc_subclass"
            if which != "cpc_at_issue"
            else "cpc_at_issue.cpc_subclass"
        )

        filters: List[Dict] = [
            {"_gte": {"patent_date": start}},
            {"_lte": {"patent_date": end}},
            {"_begins": {cpc_field: cpc_prefix}},
            {"assignees.assignee_organization": company},
        ]
        if utility_only:
            filters.append({"patent_type": "utility"})

        payload = {
            "q": {"_and": filters},
            "o": {"size": 1},
        }
        data = self._post(payload)
        total = int(data.get("total_hits", 0))
        return CountResult(total=total)

    def assignee_discover(
        self, *, prefix: str, limit: int = 400
    ) -> AssigneeList:
        """
        Best-effort discovery via patent endpoint:
        - Filter by assignees.assignee_organization begins with prefix.
        - Return distinct organizations from first page (size=min(100, limit)).
        If your deployment exposes an /assignees/ endpoint, switch to that.
        """
        size = min(100, max(1, int(limit)))
        payload = {
            "q": {"assignees.assignee_organization": {"_begins": prefix}},
            "f": [
                "assignees.assignee_organization",
                "assignees.assignee_country",
                "assignees.assignee_state",
                "assignees.assignee_city",
            ],
            "o": {"size": size, "page": 1},
        }
        data = self._post(payload)

        # Results come back as a list of patents; we need to harvest assignees.
        patents = data.get("patents", []) or []
        seen = set()
        items: List[Assignee] = []

        for p in patents:
            for a in p.get("assignees", []) or []:
                org = a.get("assignee_organization") or ""
                if not org or org in seen:
                    continue
                seen.add(org)
                items.append(
                    Assignee(
                        organization=org,
                        country=a.get("assignee_country"),
                        state=a.get("assignee_state"),
                        city=a.get("assignee_city"),
                    )
                )
                if len(items) >= limit:
                    return AssigneeList(items=items)

        return AssigneeList(items=items)
