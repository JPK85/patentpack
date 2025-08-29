from __future__ import annotations

from typing import Any, Dict, Tuple

from patentpack.providers.factory import make_provider  # type: ignore


def _post(provider, payload):
    if hasattr(provider, "_post"):
        return provider._post(payload)  # type: ignore[attr-defined]
    raise RuntimeError("Provider lacks _post(payload)")


def _year_bounds(provider, year: int):
    if hasattr(provider, "_year_bounds"):
        return provider._year_bounds(int(year))  # type: ignore[attr-defined]
    y = int(year)
    return f"{y:04d}-01-01", f"{y:04d}-12-31"


def get_provider(provider_name: str, *, rpm: int = 30):
    # provider_name examples: "uspto", "epo"
    return make_provider(provider_name, rpm=rpm)  # type: ignore
