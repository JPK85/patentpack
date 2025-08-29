from patentpack.gleif.match import rule_for, pick_top_matches


def _row(lei, legal, others=None, country="US"):
    return {
        "id": lei,
        "attributes": {
            "legalName": {"name": legal},
            "otherNames": [{"name": x} for x in (others or [])],
            "headquartersAddress": {"country": country},
        },
    }


def test_rule_for_exact_and_stem():
    # exact legal name (dot-insensitive handled inside)
    assert rule_for("ACME Inc.", "ACME Inc", []) == "exact_norm_legal"

    # exact on "other names"
    assert (
        rule_for("ACME Group", "ACME Holdings", ["ACME Group"])
        == "exact_norm_other"
    )

    # stem equality on legal (very rough check)
    assert (
        rule_for(
            "International Business Machines",
            "International Business Machine",
            [],
        )
        == "stem_eq_legal"
    )


def test_pick_top_matches_ok_and_ambiguous():
    rows = [
        _row("L1", "ACME Inc.", ["ACME"]),
        _row("L2", "ACME Incorporated"),
    ]
    matches, status, top = pick_top_matches(rows, "ACME Inc.")
    # two candidates both score as exact-ish; ambiguous top bucket
    assert status in ("ambiguous_multi", "ok")
    assert top in ("exact_norm_legal", "exact_norm_other")
    assert all("lei" in m for m in matches)

    # make it non-ambiguous by changing the second
    rows2 = [
        _row("L1", "ACME Inc.", ["ACME"]),
        _row("L2", "Different Co"),
    ]
    matches, status, top = pick_top_matches(rows2, "ACME Inc.")
    assert status == "ok"
    assert matches[0]["lei"] == "L1"
