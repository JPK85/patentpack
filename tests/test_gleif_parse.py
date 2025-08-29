from patentpack.gleif.parse import (
    as_legal_name,
    as_other_names,
    extract_names,
    pretty_first_record,
)


def test_as_legal_name_and_other_names():
    assert as_legal_name({"name": " ACME Inc. "}) == "ACME Inc."
    assert as_legal_name(" Foo ") == "Foo"
    assert as_legal_name(123) == ""

    arr = [{"name": "One"}, {"name": " Two "}, "Three", 5]
    assert as_other_names(arr) == ["One", "Two", "Three"]


def test_extract_names_attributes_and_entity():
    # attributes path
    d1 = {
        "id": "L-1",
        "attributes": {
            "legalName": {"name": "ACME AG"},
            "otherNames": [{"name": "ACME Group"}, {"name": "ACME"}],
            "headquartersAddress": {"country": "de"},
        },
    }
    legal, others, country = extract_names(d1)
    assert legal == "ACME AG"
    assert others == ["ACME Group", "ACME"]
    assert country == "DE"

    # entity fallback path
    d2 = {
        "id": "L-2",
        "attributes": {
            "entity": {
                "legalName": {"name": "Beta S.p.A."},
                "otherNames": [{"name": "Beta SpA"}],
                "headquartersAddress": {"country": "IT"},
            }
        },
    }
    legal, others, country = extract_names(d2)
    assert legal == "Beta S.p.A."
    assert others == ["Beta SpA"]
    assert country == "IT"


def test_pretty_first_record():
    rows = [
        {
            "id": "L-3",
            "attributes": {
                "legalName": {"name": "Gamma Ltd"},
                "otherNames": [{"name": "Gamma Limited"}],
                "headquartersAddress": {"country": "GB"},
            },
        }
    ]
    s = pretty_first_record(rows)
    assert '"id": "L-3"' in s
    assert '"legalName"' in s
    assert '"otherNames"' in s
    assert '"hq"' in s

    assert pretty_first_record([]) == "(no rows)"
