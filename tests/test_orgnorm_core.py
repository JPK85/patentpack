from patentpack.common.orgnorm.core import norm, cmp_norm, name_has_ascii


def test_norm_basic():
    assert norm("  Pirelli & C SpA  ") == "pirelli and c spa"
    assert norm("C.") == "c"  # single-letter dots collapse
    assert norm("A/B") == "a/b"  # allowed punctuation preserved


def test_cmp_norm_strips_adr():
    assert (
        cmp_norm("SAMSUNG ELECTRONICS CO., LTD. (ADR)")
        == "samsung electronics co ltd"
    )


def test_name_has_ascii():
    assert name_has_ascii("株式会社ソニー SONY") is True
    assert name_has_ascii("株式会社ソニー") is False
