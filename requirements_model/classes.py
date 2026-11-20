"""Defines the types of requirement changes an upgrade can propose."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class RequirementClass(Enum):
    RETAIN = "RETAIN"
    ADD = "ADD"
    WAIVE = "WAIVE"
    SUPERSEDE = "SUPERSEDE"
    CONDITIONAL = "CONDITIONAL"
    CONFLICT = "CONFLICT"

@dataclass(frozen=True)
class Requirement:
    id: str
    req_class: RequirementClass
    target_metric: str
    bound: float
    scope_text: Optional[str] = None # e.g., "class == 'BULK'"
