import os

import pytest

from patentpack.gleif.http import make_session as _make_gleif_session

# Load .env if present, but don't fail if it's missing.
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

# ---- env helpers ------------------------------------------------------------

PV_KEY = os.getenv("PATENTPACK_PV_KEY", "")
OPS_KEY = os.getenv("OPS_KEY", "")
OPS_SECRET = os.getenv("OPS_SECRET", "")

have_uspto = bool(PV_KEY)
have_epo = bool(OPS_KEY and OPS_SECRET)


def require_env(flag: bool, why: str):
    if not flag:
        pytest.skip(f"env not configured: {why}")


# ---- fixtures ---------------------------------------------------------------


@pytest.fixture(scope="session")
def gleif_session():
    """Live GLEIF session; skipped if no internet (no specific env needed)."""
    return _make_gleif_session()


@pytest.fixture(scope="session")
def uspto_provider():
    """Live USPTO provider; requires PATENTPACK_PV_KEY."""
    require_env(have_uspto, "PATENTPACK_PV_KEY")
    from patentpack.providers.uspto import UsptoProvider

    return UsptoProvider(api_key=PV_KEY, rpm=30)


@pytest.fixture(scope="session")
def epo_provider():
    """Live EPO provider; requires OPS_KEY + OPS_SECRET."""
    require_env(have_epo, "OPS_KEY/OPS_SECRET")
    from patentpack.providers.epo import EpoProvider

    return EpoProvider(key=OPS_KEY, secret=OPS_SECRET, rpm=30)
