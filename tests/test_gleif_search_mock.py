import types
from patentpack.gleif import search as search_mod


def test_gleif_search_union_mock(monkeypatch):
    # Keep query space tiny & predictable
    monkeypatch.setattr(
        search_mod,
        "expand_query_variants",
        lambda name: ["Foo Inc", "Foo Incorporated"],
    )
    monkeypatch.setattr(
        search_mod, "country_hints_from_name", lambda name: ["US"]
    )

    calls = []

    # Fake safe_get: respond based on filters; dedupe by LEI
    def fake_safe_get(session, params):
        calls.append(params)
        # Responses:
        # - legalName=Foo Inc -> L1
        # - legalName=Foo Inc + country=US -> L1 (duplicate)
        # - fulltext=Foo Incorporated -> L2
        # others -> empty
        data = []
        if (
            params.get("filter[entity.legalName]") == "Foo Inc"
            and "filter[entity.legalAddress.country]" not in params
        ):
            data = [
                {
                    "id": "L1",
                    "attributes": {
                        "lei": "L1",
                        "entity": {"legalName": {"name": "Foo Inc"}},
                    },
                }
            ]
        elif (
            params.get("filter[entity.legalName]") == "Foo Inc"
            and params.get("filter[entity.legalAddress.country]") == "US"
        ):
            data = [
                {"id": "L1", "attributes": {"lei": "L1"}}
            ]  # duplicate to test union
        elif params.get("filter[fulltext]") == "Foo Incorporated":
            data = [{"id": "L2", "attributes": {"lei": "L2"}}]
        return {"data": data}, 200, "ok"

    monkeypatch.setattr(search_mod, "safe_get", fake_safe_get)

    # Session object is unused by fake_safe_get but pass a dummy for signature
    dummy_session = types.SimpleNamespace()

    rows = search_mod.gleif_search_union(
        dummy_session, "Foo Inc", page_size=5, debug=False
    )
    leis = sorted(
        [r.get("id") or r.get("attributes", {}).get("lei") for r in rows]
    )

    # Expect L1 & L2 exactly once each
    assert leis == ["L1", "L2"]

    # Sanity: we actually hit a few distinct query shapes
    keys_seen = {tuple(sorted(k for k in p.keys())) for p in calls}
    assert any("filter[entity.legalName]" in ks for ks in keys_seen)
    assert any("filter[fulltext]" in ks for ks in keys_seen)
