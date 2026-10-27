"""Versioned key-value store with an append-only write log.

Every write bumps a global version counter and appends a log entry. This is what lets
later phases (a) see state-level dependencies (a read of a key written by a faulty step)
and (b) roll the store back to any earlier version.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

_MISSING = object()


@dataclass
class LogEntry:
    version: int          # global version after this write
    key: str
    old: Any              # value before the write (None if the key did not exist)
    new: Any              # value after the write
    actor: str            # agent or tool that wrote it
    step: int | None = None


@dataclass
class StateStore:
    data: dict[str, Any] = field(default_factory=dict)
    log: list[LogEntry] = field(default_factory=list)
    version: int = 0

    def get(self, key: str, default: Any = None) -> Any:
        return copy.deepcopy(self.data.get(key, default))

    def exists(self, key: str) -> bool:
        return key in self.data

    def set(self, key: str, value: Any, actor: str = "unknown", step: int | None = None) -> int:
        old = self.data.get(key, None)
        self.version += 1
        self.data[key] = copy.deepcopy(value)
        self.log.append(LogEntry(self.version, key, copy.deepcopy(old), copy.deepcopy(value), actor, step))
        return self.version

    def key_version(self, key: str) -> int:
        """Version of the last write to `key` (0 if never written)."""
        for entry in reversed(self.log):
            if entry.key == key:
                return entry.version
        return 0

    def writes_by(self, actor: str) -> list[LogEntry]:
        return [e for e in self.log if e.actor == actor]

    def rollback_to(self, version: int) -> None:
        """Undo every write after `version`, newest first, and truncate the log."""
        if not 0 <= version <= self.version:
            raise ValueError(f"version {version} out of range 0..{self.version}")
        while self.log and self.log[-1].version > version:
            entry = self.log.pop()
            if entry.old is None:
                self.data.pop(entry.key, None)
            else:
                self.data[entry.key] = copy.deepcopy(entry.old)
        self.version = version

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self.data)
