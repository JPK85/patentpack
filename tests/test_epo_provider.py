import pytest

from patentpack.core.contracts import CountResult
from patentpack.providers.epo import EpoProvider


def test_epo_count_cpc_year_mock(monkeypatch):
    recorded = {}

    def fake_count_for_query(self, query: str) -> int:
        recorded["query"] = query
        # canned total
        return 10_000  # OPS caps total-result-count at 10k

    monkeypatch.setattr(EpoProvider, "_count_for_query", fake_count_for_query)

    p = EpoProvider(key="DUMMY", secret="DUMMY", rpm=999, debug=False)
    res: CountResult = p.count_by_cpc_year(year=2021, cpc="Y02")

    assert res.total == 10_000

    q = recorded["query"]
    # basic OPS CQL shape checks
    assert "cpc=/low Y02" in q
    assert 'pd within "20210101 20211231"' in q
    # no applicant filter for the year-only variant
    assert "applicant =" not in q


def test_epo_count_cpc_company_year_mock(monkeypatch):
    recorded = {}

    def fake_count_for_query(self, query: str) -> int:
        recorded["query"] = query
        return 772

    monkeypatch.setattr(EpoProvider, "_count_for_query", fake_count_for_query)

    p = EpoProvider(key="DUMMY", secret="DUMMY", rpm=999, debug=False)
    res = p.count_by_cpc_company_year(
        year=2019, cpc="Y02", company="Volkswagen AG"
    )

    assert res.total == 772

    q = recorded["query"]
    assert 'applicant="Volkswagen AG"' in q
    assert "cpc=/low Y02" in q
    assert 'pd within "20190101 20191231"' in q
