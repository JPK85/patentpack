"""
GLEIF (Global Legal Entity Identifier Foundation) integration utilities.

This subpackage provides:
- HTTP client wrappers for the GLEIF API (`http.py`)
- Query expansion and normalization for organization names (`normalize/`)
- Structured parsing of GLEIF API responses (`parse.py`)
- Candidate matching and ranking rules (`match.py`)
- High-level search orchestration (`search.py`)

Typical usage:
    from patentpack.gleif.search import gleif_search_union
    from patentpack.gleif.match import pick_top_matches
"""
