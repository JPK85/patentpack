from patentpack.common.orgnorm.variants import expand_query_variants


def test_variants_spa_and_the():
    vs = expand_query_variants("Pirelli & C SpA")
    # keep original first
    assert vs[0] == "Pirelli & C SpA"
    # ensure canonical dotted & spelled forms appear
    assert any("S.p.A." in v for v in vs)
    assert any("Società per Azioni" in v for v in vs)
    # "The ..." variants included
    assert any(v.startswith("The ") for v in vs)


def test_variants_suffix_full_forms():
    vs = expand_query_variants("SKF AB")
    assert "AB SKF" in vs or "Aktiebolaget SKF" in vs
    # ensure we can also drop trailing single-token corp suffix for FT search
    assert "SKF" in vs
