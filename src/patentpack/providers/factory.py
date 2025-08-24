from __future__ import annotations

from typing import Any

from ..core.contracts import Provider
from ..core.interfaces import PatentProvider
from .epo import EpoProvider
from .uspto import UsptoProvider


def make_provider(provider: Provider, **kwargs: Any) -> PatentProvider:
    if provider == Provider.USPTO:
        return UsptoProvider(**kwargs)
    if provider == Provider.EPO:
        return EpoProvider(**kwargs)
    raise ValueError(f"Unknown provider: {provider}")
