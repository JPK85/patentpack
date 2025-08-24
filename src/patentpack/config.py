"""
Global configuration for patentpack.
Only infrastructure knobs live here (paths, URLs, retries, RPM, creds).
No CPC- or operation-specific hardcoding. Use the filename builders below.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final, List, Optional

from dotenv import load_dotenv

load_dotenv()

# -----------------------------------------------------------------------------
# Storage roots
# -----------------------------------------------------------------------------
DATA_DIR: Final[Path] = Path(__file__).resolve().parents[2] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

OUT_DIR: Final[Path] = Path(os.getenv("PATENTPACK_OUT_DIR", DATA_DIR / "out"))
CACHE_DIR: Final[Path] = Path(
    os.getenv("PATENTPACK_CACHE_DIR", DATA_DIR / "cache")
)
OUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------------------------------------------------------
# Generic filename builders
# -----------------------------------------------------------------------------
def per_year_filename(
    *,
    year: int,
    op: str,  # "operation" e.g., "counts", "list", "timeseries"
    provider: Optional[str] = None,  # e.g., "uspto", "epo"
    cpc: Optional[str] = None,  # e.g., "Y02"
    suffix: str = "csv",
    prefix: str = "pp",  # "pp" for patentpack
) -> Path:
    """
    Build a consistent per-year artifact filename like:
      pp_counts_2019_uspto_Y02.csv
      pp_list_2021_epo.csv
    Only includes provider/cpc parts if supplied.
    """
    parts = [prefix, op, f"{year:04d}"]
    if provider:
        parts.append(provider.lower())
    if cpc:
        parts.append(cpc.upper())
    fname = "_".join(parts) + f".{suffix.lstrip('.')}"
    return OUT_DIR / fname


def panel_filename(
    *,
    op: str,  # e.g., "counts_company_year"
    provider: Optional[str] = None,
    cpc: Optional[str] = None,
    suffix: str = "csv",
    prefix: str = "pp",
) -> Path:
    """
    Panel-style artifact (multi-year/multi-entity), e.g.:
      pp_counts_company_year_uspto_Y02.csv
    """
    parts = [prefix, op]
    if provider:
        parts.append(provider.lower())
    if cpc:
        parts.append(cpc.upper())
    fname = "_".join(parts) + f".{suffix.lstrip('.')}"
    return OUT_DIR / fname


def snapshot_filename(
    *,
    name: str,  # e.g., "assignee_discover", "citations", "families"
    provider: Optional[str] = None,
    cpc: Optional[str] = None,
    when: Optional[str] = None,  # e.g., "2025-08-24", "v1"
    suffix: str = "csv",
    prefix: str = "pp",
) -> Path:
    """
    Generic snapshot artifact (not tied to a single year), e.g.:
      pp_assignee_discover_uspto_Y02_2025-08-24.csv
    """
    parts = [prefix, name]
    if provider:
        parts.append(provider.lower())
    if cpc:
        parts.append(cpc.upper())
    if when:
        parts.append(when)
    fname = "_".join(parts) + f".{suffix.lstrip('.')}"
    return OUT_DIR / fname


# -----------------------------------------------------------------------------
# HTTP / retry / pacing
# -----------------------------------------------------------------------------
DEFAULT_TIMEOUT_S: Final[int] = int(os.getenv("PATENTPACK_TIMEOUT_S", "45"))

RETRY_STATUS_FORCELIST: Final[List[int]] = [429, 500, 502, 503, 504]
RETRY_BACKOFF_FACTOR: Final[float] = float(
    os.getenv("PATENTPACK_RETRY_BACKOFF", "1.0")
)
RETRY_ALLOWED_METHODS: Final[List[str]] = ["GET", "POST"]

# RPM limits (applied similarly across providers unless overridden)
DEFAULT_RPM: Final[int] = int(os.getenv("PATENTPACK_DEFAULT_RPM", "40"))
MAX_RPM: Final[int] = int(os.getenv("PATENTPACK_MAX_RPM", "44"))

# -----------------------------------------------------------------------------
# Provider base URLs / credentials; overridden by .env vars
# -----------------------------------------------------------------------------
# USPTO (PatentsView/PatentSearch)
PATENTSEARCH_API_URL: Final[str] = os.getenv(
    "PATENTPACK_PV_URL", "https://search.patentsview.org/api/v1/patent/"
)
PATENTSEARCHKEY: Final[str] = os.getenv("PATENTPACK_PV_KEY", "")

# EPO OPS
OPS_AUTH_URL: Final[str] = os.getenv(
    "PATENTPACK_OPS_AUTH_URL", "https://ops.epo.org/3.2/auth/accesstoken"
)
OPS_SEARCH_URL: Final[str] = os.getenv(
    "PATENTPACK_OPS_SEARCH_URL",
    "https://ops.epo.org/3.2/rest-services/published-data/search",
)


def get_env(
    name: str, *, required: bool = False, default: Optional[str] = None
) -> Optional[str]:
    """Small helper to fetch env vars with an optional 'required' flag."""
    val = os.getenv(name, default)
    if required and not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


def epo_key(required: bool = False) -> Optional[str]:
    return get_env("OPS_KEY", required=required)


def epo_secret(required: bool = False) -> Optional[str]:
    return get_env("OPS_SECRET", required=required)


# -----------------------------------------------------------------------------
# Public exports
# -----------------------------------------------------------------------------
__all__ = [
    # roots
    "DATA_DIR",
    "OUT_DIR",
    "CACHE_DIR",
    # builders
    "per_year_filename",
    "panel_filename",
    "snapshot_filename",
    # http/retry/pacing
    "DEFAULT_TIMEOUT_S",
    "RETRY_STATUS_FORCELIST",
    "RETRY_BACKOFF_FACTOR",
    "RETRY_ALLOWED_METHODS",
    "DEFAULT_RPM",
    "MAX_RPM",
    # providers
    "PATENTSEARCH_API_URL",
    "PATENTSEARCHKEY",
    "OPS_AUTH_URL",
    "OPS_SEARCH_URL",
    # env helpers
    "get_env",
    "epo_key",
    "epo_secret",
]
