import os
from typing import Any, Dict

import pytest

# Load .env if present, but don't fail if it's missing.
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

# ---- mode & env flags -------------------------------------------------------


def _truthy(s: str | None) -> bool:
    return str(s).strip().lower() in {"1", "true", "yes", "on"}


LIVE = _truthy(os.getenv("PATENTPACK_LIVE_TESTS"))

PV_KEY = os.getenv("PATENTPACK_PV_KEY", "")
OPS_KEY = os.getenv("OPS_KEY", "")
OPS_SECRET = os.getenv("OPS_SECRET", "")

have_uspto = bool(PV_KEY)
have_epo = bool(OPS_KEY and OPS_SECRET)


# ---- optional live GLEIF session -------------------------------------------


@pytest.fixture(scope="session")
def gleif_session():
    """
    Live GLEIF session; only created in LIVE mode.
    Otherwise skipped to avoid any network.
    """
    if not LIVE:
        pytest.skip("gleif_session skipped (offline mode)")
    from patentpack.gleif.http import make_session as _make_gleif_session

    return _make_gleif_session()


# =============================================================================
# MOCK HELPERS (used when PATENTPACK_LIVE_TESTS is NOT set)
# =============================================================================


def _mock_uspto_post(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Emulate PatentsView /api/v1/patent/ count responses.
    Returns {"total_hits": <int>} deterministically from the CPC prefix.
    """
    # Extract a CPC prefix from the payload (handles both year and company queries)
    cpc_prefix = "Y02"
    try:
        filters = payload.get("q", {}).get("_and", [])
        for f in filters:
            if "_begins" in f:
                begins = f["_begins"]
                # cpc_current.cpc_subclass or cpc_at_issue.cpc_subclass -> value like "B60"
                cpc_prefix = next(iter(begins.values()))
                break
    except Exception:
        pass

    cpc_prefix = (cpc_prefix or "").upper()

    # Deterministic but varied mock counts by CPC class
    # (enough for assertions like >0, !=0, etc.)
    table = {
        "Y02": 10,
        "B60": 9,
        "H01": 6,
        "G06": 12,
        "H04": 8,
    }
    total = table.get(cpc_prefix[:3], 3)
    return {"error": False, "count": 0, "total_hits": total, "patents": []}


def _mock_epo_count_for_query(query: str) -> int:
    """
    Emulate EPO OPS count_for_query() by inspecting the CQL.
    Looks for 'cpc=/low <CLASS>' and returns a deterministic count.
    """
    # crude parse: find 'cpc =/low ' then take next token
    q = query.upper()
    needle = "CPC =/LOW "
    cls = "Y02"
    try:
        if needle in q:
            start = q.index(needle) + len(needle)
            cls = q[start : start + 3]
    except Exception:
        pass

    table = {
        "Y02": 772,
        "B60": 1315,
        "H01": 423,
        "G06": 1200,
        "H04": 850,
    }
    return table.get(cls, 5)


# =============================================================================
# PROVIDER FIXTURES
# =============================================================================


@pytest.fixture(scope="session")
def uspto_provider():
    """
    Provider fixture:
      - Offline (default): returns a UsptoProvider with its HTTP POST mocked.
      - Live (PATENTPACK_LIVE_TESTS=1): real provider (requires PATENTPACK_PV_KEY).
    """
    from patentpack.providers.uspto import UsptoProvider

    if LIVE:
        if not have_uspto:
            pytest.skip("PATENTPACK_PV_KEY missing for live USPTO tests")
        return UsptoProvider(api_key=PV_KEY, rpm=30)

    # Offline: build provider and monkeypatch its _post method.
    p = UsptoProvider(api_key="DUMMY", rpm=30, debug=False)

    # Monkeypatch the instance method without touching the class.
    def _post_stub(payload: Dict[str, Any]) -> Dict[str, Any]:
        return _mock_uspto_post(payload)

    p._post = _post_stub  # type: ignore[attr-defined]
    return p


@pytest.fixture(scope="session")
def epo_provider():
    """
    Provider fixture:
      - Offline (default): returns an EpoProvider with _count_for_query mocked.
      - Live (PATENTPACK_LIVE_TESTS=1): real provider (requires OPS_KEY/OPS_SECRET).
    """
    from patentpack.providers.epo import EpoProvider

    if LIVE:
        if not have_epo:
            pytest.skip("OPS_KEY/OPS_SECRET missing for live EPO tests")
        return EpoProvider(key=OPS_KEY, secret=OPS_SECRET, rpm=30)

    # Offline: build provider with dummy creds and monkeypatch count method.
    p = EpoProvider(key="DUMMY", secret="DUMMY", rpm=30, debug=False)

    def _count_stub(query: str) -> int:
        return _mock_epo_count_for_query(query)

    p._count_for_query = _count_stub  # type: ignore[attr-defined]
    return p


# =============================================================================
# PYTEST MARKER HANDLING
# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    # Register a 'live' marker for any tests that explicitly want real I/O.
    config.addinivalue_line("markers", "live: test requires live API access")


def pytest_runtest_setup(item: pytest.Item) -> None:
    # If a test is marked live but we're not in LIVE mode, skip it proactively.
    if "live" in item.keywords and not LIVE:
        pytest.skip("live test skipped (PATENTPACK_LIVE_TESTS not enabled)")
