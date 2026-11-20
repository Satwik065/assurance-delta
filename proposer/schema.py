"""Defines the JSON structure of a Migration Proposal (Gate G1)."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class RequirementChange:
    id: str
    req_class: str
    target_metric: str
    new_bound: float
    scope_text: str | None

@dataclass(frozen=True)
class MigrationProposal:
    code_path: str
    changes: list[RequirementChange]
