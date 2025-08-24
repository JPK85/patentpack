from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class Provider(str, Enum):
    USPTO = "uspto"
    EPO = "epo"


@dataclass(frozen=True)
class CountResult:
    total: int
    meta: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class Assignee:
    organization: str
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None


@dataclass(frozen=True)
class AssigneeList:
    items: List[Assignee]
