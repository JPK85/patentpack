import pytest

from patentpack.providers.uspto import UsptoProvider
from patentpack.core.contracts import CountResult


def test_uspto_count_cpc_year_mock(monkeypatch):
    calls = {}

    def fake_post(self, payload):
        # capture what we send
        calls["payload"] = payload
        # return a canned PatentsView-like response
        return {"error": False, "count": 1, "total_hits": 35263, "patents": []}

    monkeypatch.setattr(UsptoProvider, "_post", fake_post)

    p = UsptoProvider(api_key="DUMMY", rpm=999, debug=False)
    res: CountResult = p.count_by_cpc_year(year=2019, cpc="y02")

    # behavior
    assert isinstance(res.total, int)
    assert res.total == 35263

    # request shape
    q = calls["payload"]["q"]["_and"]
    # dates present
    assert {"_gte": {"patent_date": "2019-01-01"}} in q
    assert {"_lte": {"patent_date": "2019-12-31"}} in q
    # cpc prefix filter (normalized to current by default)
    assert any(("_begins" in f) and ("cpc_current.cpc_subclass" in next(iter(f["_begins"]))) for f in q)
    assert any(f.get("_begins", {}).get("cpc_current.cpc_subclass") == "Y02" for f in q)
    # size=1 (we only need the count)
    assert calls["payload"]["o"]["size"] == 1


def test_uspto_count_cpc_company_year_mock(monkeypatch):
    calls = {}

    def fake_post(self, payload):
        calls["payload"] = payload
        return {"error": False, "count": 1, "total_hits": 9, "patents": []}

    monkeypatch.setattr(UsptoProvider, "_post", fake_post)

    p = UsptoProvider(api_key="DUMMY", rpm=999, debug=False)
    res = p.count_by_cpc_company_year(year=2019, cpc="B60", company="Ford Motor Company")

    assert res.total == 9

    q = calls["payload"]["q"]["_and"]
    # company filter present
    assert {"assignees.assignee_organization": "Ford Motor Company"} in q
    # cpc prefix normalized
    assert any(f.get("_begins", {}).get("cpc_current.cpc_subclass") == "B60" for f in q)
