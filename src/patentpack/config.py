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
# XDG cache location: ~/.cache/patentpack (or $XDG_CACHE_HOME/patentpack)
_XDG_CACHE_HOME = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
CACHE_DIR = _XDG_CACHE_HOME / "patentpack"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------------------------------------------------------
# Generic filename builders
# -----------------------------------------------------------------------------
def _join(base_dir: Optional[Path], fname: str) -> Path:
    return (base_dir / fname) if base_dir else Path(fname)


def per_year_filename(
    *,
    year: int,
    op: str,
    provider: Optional[str] = None,
    cpc: Optional[str] = None,
    suffix: str = "csv",
    prefix: str = "pp",
    base_dir: Optional[Path] = None,
) -> Path:
    parts = [prefix, op, f"{year:04d}"]
    if provider:
        parts.append(provider.lower())
    if cpc:
        parts.append(cpc.upper())
    fname = "_".join(parts) + f".{suffix.lstrip('.')}"
    return _join(base_dir, fname)


def panel_filename(
    *,
    op: str,  # e.g., "counts_company_year"
    provider: Optional[str] = None,
    cpc: Optional[str] = None,
    suffix: str = "csv",
    prefix: str = "pp",
    base_dir: Optional[Path] = None,
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
    return _join(base_dir, fname)


def snapshot_filename(
    *,
    name: str,  # e.g., "assignee_discover", "citations", "families"
    provider: Optional[str] = None,
    cpc: Optional[str] = None,
    when: Optional[str] = None,  # e.g., "2025-08-24", "v1"
    suffix: str = "csv",
    prefix: str = "pp",
    base_dir: Optional[Path] = None,
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
    return _join(base_dir, fname)


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
