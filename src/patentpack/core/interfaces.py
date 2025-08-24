from __future__ import annotations

from typing import Literal, Optional, Protocol

from .contracts import AssigneeList, CountResult

Which = Literal["cpc_current", "cpc_at_issue"]


class PatentProvider(Protocol):
    """
    Unified provider surface. Implementations must provide these methods.
    """

    def set_rpm(self, rpm: int) -> None: ...

    def count_by_cpc_year(
        self,
        *,
        year: int,
        cpc: str,
        which: Optional[Which] = None,
        utility_only: bool = False,
    ) -> CountResult: ...

    def count_by_cpc_company_year(
        self,
        *,
        year: int,
        cpc: str,
        company: str,
        which: Optional[Which] = None,
        utility_only: bool = False,
    ) -> CountResult: ...

    def assignee_discover(
        self, *, prefix: str, limit: int = 400
    ) -> AssigneeList: ...
