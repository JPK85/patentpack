import pytest


@pytest.mark.live
@pytest.mark.uspto
def test_uspto_count_cpc_company_year(uspto_provider):
    res = uspto_provider.count_by_cpc_company_year(
        year=2021, cpc="Y02", company="BASF SE"
    )
    # regression guard: expect some activity but not > 10k
    assert 1 <= res.total <= 10000


@pytest.mark.live
@pytest.mark.uspto
def test_uspto_count_cpc_year(uspto_provider):
    res = uspto_provider.count_by_cpc_year(year=2021, cpc="Y02")
    # Expect at least some results; exact upper bound varies over time.
    assert isinstance(res.total, int)
    assert res.total >= 100  # loose lower bound to guard regressions
