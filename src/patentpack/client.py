from __future__ import annotations

from typing import Optional

from .core.contracts import AssigneeList, CountResult, Provider
from .providers.factory import make_provider


class PatentPack:
    """
    Public façade. Does not implement provider logic itself.
    Delegates to a provider instance selected by `Provider`.
    """

    def __init__(self, provider: Provider, **provider_kwargs) -> None:
        self._provider = make_provider(provider, **provider_kwargs)

    def set_rpm(self, rpm: int) -> None:
        self._provider.set_rpm(rpm)

    def count_cpc_year(
        self,
        *,
        year: int,
        cpc: str,
        which: Optional[str] = None,
        utility_only: bool = False,
    ) -> CountResult:
        return self._provider.count_by_cpc_year(
            year=year, cpc=cpc, which=which, utility_only=utility_only
        )

    def count_cpc_company_year(
        self,
        *,
        year: int,
        cpc: str,
        company: str,
        which: Optional[str] = None,
        utility_only: bool = False,
    ) -> CountResult:
        return self._provider.count_by_cpc_company_year(
            year=year,
            cpc=cpc,
            company=company,
            which=which,
            utility_only=utility_only,
        )

    def assignee_discover(
        self, *, prefix: str, limit: int = 400
    ) -> AssigneeList:
        return self._provider.assignee_discover(prefix=prefix, limit=limit)
