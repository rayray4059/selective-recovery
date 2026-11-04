# key-value store that logs every write so it can roll back
import copy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LogEntry:
    version: int
    key: str
    old: Any
    new: Any
    actor: str
    step: int = None


@dataclass
class StateStore:
    data: dict = field(default_factory=dict)
    log: list = field(default_factory=list)
    version: int = 0

    def get(self, key, default=None):
        return copy.deepcopy(self.data.get(key, default))

    def exists(self, key):
        return key in self.data

    def set(self, key, value, actor="unknown", step=None):
        old = self.data.get(key, None)
        self.version += 1
        self.data[key] = copy.deepcopy(value)
        self.log.append(LogEntry(self.version, key, copy.deepcopy(old), copy.deepcopy(value), actor, step))
        return self.version

    def key_version(self, key):
        for entry in reversed(self.log):
            if entry.key == key:
                return entry.version
        return 0

    def writes_by(self, actor):
        return [e for e in self.log if e.actor == actor]

    def rollback_to(self, version):
        if not 0 <= version <= self.version:
            raise ValueError(f"version {version} out of range 0..{self.version}")
        while self.log and self.log[-1].version > version:
            entry = self.log.pop()
            if entry.old is None:
                self.data.pop(entry.key, None)
            else:
                self.data[entry.key] = copy.deepcopy(entry.old)
        self.version = version

    def snapshot(self):
        return copy.deepcopy(self.data)
