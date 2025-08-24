import pytest


@pytest.mark.live
@pytest.mark.epo
def test_epo_count_cpc_company_year(epo_provider):
    # TESLA INC variant returns nonzero for Y02 in 2021
    res = epo_provider.count_by_cpc_company_year(
        year=2021, cpc="Y02", company="TESLA INC"
    )
    assert 1 <= res.total <= 10000


@pytest.mark.live
@pytest.mark.epo
def test_epo_count_cpc_year(epo_provider):
    res = epo_provider.count_by_cpc_year(year=2021, cpc="Y02")
    # OPS caps totals at 10k; minimal sanity bound:
    assert 1 <= res.total <= 10000
