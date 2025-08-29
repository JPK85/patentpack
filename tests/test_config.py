from __future__ import annotations

import os
from pathlib import Path

import pytest

import patentpack.config as cfg


def test_cache_dir_defaults_to_xdg(tmp_path, monkeypatch):
    # Point XDG cache to a temp dir so we don't touch the real filesystem.
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    # Reload module to re-evaluate constants with new env.
    import importlib

    importlib.reload(cfg)

    expected = Path(os.environ["XDG_CACHE_HOME"]) / "patentpack"
    assert cfg.CACHE_DIR == expected
    assert expected.exists() and expected.is_dir()


def test_filename_builders_default_relative(tmp_path, monkeypatch):
    # Ensure no base_dir is passed → return relative Path(fname)
    # No need to patch XDG here; we are testing only builders.
    p1 = cfg.per_year_filename(
        year=2019, op="counts", provider="uspto", cpc="Y02"
    )
    assert isinstance(p1, Path)
    assert p1.name == "pp_counts_2019_uspto_Y02.csv"
    assert not p1.is_absolute()

    p2 = cfg.panel_filename(
        op="counts_company_year", provider="epo", cpc="H01"
    )
    assert p2.name == "pp_counts_company_year_epo_H01.csv"
    assert not p2.is_absolute()

    p3 = cfg.snapshot_filename(
        name="assignee_discover",
        provider="uspto",
        cpc="Y02",
        when="2025-08-24",
    )
    assert p3.name == "pp_assignee_discover_uspto_Y02_2025-08-24.csv"
    assert not p3.is_absolute()


def test_filename_builders_with_base_dir(tmp_path):
    # When base_dir is provided, returned path must be under it.
    base = tmp_path / "out"
    p1 = cfg.per_year_filename(year=2020, op="list", base_dir=base)
    assert p1.parent == base
    assert p1.name == "pp_list_2020.csv"

    p2 = cfg.panel_filename(
        op="counts_company_year", base_dir=base, suffix="parquet", prefix="ppx"
    )
    assert p2.parent == base
    assert p2.name == "ppx_counts_company_year.parquet"

    p3 = cfg.snapshot_filename(
        name="families", base_dir=base, when="v1", suffix="jsonl"
    )
    assert p3.parent == base
    assert p3.name == "pp_families_v1.jsonl"


def test_http_retry_defaults_from_env(monkeypatch):
    # Set env and reload to verify parsing behavior.
    monkeypatch.setenv("PATENTPACK_TIMEOUT_S", "33")
    monkeypatch.setenv("PATENTPACK_RETRY_BACKOFF", "2.5")
    monkeypatch.setenv("PATENTPACK_DEFAULT_RPM", "41")
    monkeypatch.setenv("PATENTPACK_MAX_RPM", "55")

    import importlib

    importlib.reload(cfg)

    assert cfg.DEFAULT_TIMEOUT_S == 33
    assert cfg.RETRY_BACKOFF_FACTOR == 2.5
    assert cfg.DEFAULT_RPM == 41
    assert cfg.MAX_RPM == 55

    # Sanity: allowed methods and forcelist are hard-coded
    assert cfg.RETRY_ALLOWED_METHODS == ["GET", "POST"]
    assert cfg.RETRY_STATUS_FORCELIST == [429, 500, 502, 503, 504]


def test_provider_urls_and_keys_from_env(monkeypatch):
    monkeypatch.setenv(
        "PATENTPACK_PV_URL", "https://example.test/api/v1/patent/"
    )
    monkeypatch.setenv("PATENTPACK_PV_KEY", "ABC123")
    monkeypatch.setenv(
        "PATENTPACK_OPS_AUTH_URL", "https://ops.example.test/auth"
    )
    monkeypatch.setenv(
        "PATENTPACK_OPS_SEARCH_URL", "https://ops.example.test/search"
    )

    import importlib

    importlib.reload(cfg)

    assert cfg.PATENTSEARCH_API_URL == "https://example.test/api/v1/patent/"
    assert cfg.PATENTSEARCHKEY == "ABC123"
    assert cfg.OPS_AUTH_URL == "https://ops.example.test/auth"
    assert cfg.OPS_SEARCH_URL == "https://ops.example.test/search"


def test_get_env_required_ok(monkeypatch):
    monkeypatch.setenv("X_TEST_KEY", "ok")
    assert cfg.get_env("X_TEST_KEY", required=True) == "ok"


def test_get_env_required_missing(monkeypatch):
    monkeypatch.delenv("X_MISSING_KEY", raising=False)
    with pytest.raises(RuntimeError):
        cfg.get_env("X_MISSING_KEY", required=True)


def test_epo_key_secret_helpers(monkeypatch):
    monkeypatch.setenv("OPS_KEY", "K")
    monkeypatch.setenv("OPS_SECRET", "S")
    assert cfg.epo_key(required=True) == "K"
    assert cfg.epo_secret(required=True) == "S"
