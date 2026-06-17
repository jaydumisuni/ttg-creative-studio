#!/usr/bin/env python3
"""Undo/redo history for TTG Creative Studio projects."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

from ttg_project_schema import TTGProject


@dataclass
class HistoryState:
    label: str
    project: TTGProject


@dataclass
class ProjectHistory:
    max_depth: int = 50
    undo_stack: list[HistoryState] = field(default_factory=list)
    redo_stack: list[HistoryState] = field(default_factory=list)

    def remember(self, label: str, project: TTGProject) -> None:
        self.undo_stack.append(HistoryState(label=label, project=deepcopy(project)))
        if len(self.undo_stack) > self.max_depth:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def can_undo(self) -> bool:
        return bool(self.undo_stack)

    def can_redo(self) -> bool:
        return bool(self.redo_stack)

    def undo(self, current: TTGProject, label: str = "redo snapshot") -> TTGProject:
        if not self.undo_stack:
            return current
        self.redo_stack.append(HistoryState(label=label, project=deepcopy(current)))
        return deepcopy(self.undo_stack.pop().project)

    def redo(self, current: TTGProject, label: str = "undo snapshot") -> TTGProject:
        if not self.redo_stack:
            return current
        self.undo_stack.append(HistoryState(label=label, project=deepcopy(current)))
        return deepcopy(self.redo_stack.pop().project)

    def clear(self) -> None:
        self.undo_stack.clear()
        self.redo_stack.clear()
