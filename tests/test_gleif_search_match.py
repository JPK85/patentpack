import pytest

from patentpack.gleif.search import gleif_search_union
from patentpack.gleif.match import pick_top_matches


@pytest.mark.live
@pytest.mark.gleif
def test_gleif_tesla_exact_match(gleif_session):
    rows = gleif_search_union(gleif_session, "TESLA INC", debug=False)
    matches, status, rule = pick_top_matches(rows, "TESLA INC")
    assert status in {"ok", "ambiguous_multi"}
    # this LEI has been stable for years, but in case of data drift, allow fallback:
    if status == "ok":
        top = matches[0]
        assert top["legal"].lower().startswith("tesla")
        # if it ever changes, this assertion can be relaxed:
        assert top["lei"] in {"54930043XZGB27CTOV49"}
