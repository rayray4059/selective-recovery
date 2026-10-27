"""Simulated tools over a versioned store, a workspace folder, a refunds ledger and an outbox.

Reversibility (matters for Phase 2 recovery):
  read_record    read-only
  update_record  reversible via the store's write log
  write_file     reversible via workspace snapshot (see snapshots.py, added later)
  issue_refund   compensable: a reversal entry can be appended, the original stays
  send_message   NOT reversible: the outbox is treated as already seen
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from env.state_store import StateStore


class ToolError(Exception):
    pass


@dataclass
class Environment:
    store: StateStore
    workspace: Path
    ledger: list[dict] = field(default_factory=list)
    outbox: list[dict] = field(default_factory=list)
    calls: list[dict] = field(default_factory=list)   # every tool call, in order
    step: int = 0

    def __post_init__(self) -> None:
        self.workspace = Path(self.workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)

    # ---- dispatch -------------------------------------------------------------------
    def call(self, tool: str, actor: str, **args: Any) -> dict:
        fn = getattr(self, f"_tool_{tool}", None)
        record = {"tool": tool, "actor": actor, "args": args, "step": self.step,
                  "t": time.time(), "version_before": self.store.version}
        if fn is None:
            record.update(status="error", error=f"unknown tool {tool!r}")
            self.calls.append(record)
            raise ToolError(record["error"])
        try:
            result = fn(actor=actor, **args)
        except ToolError as exc:
            record.update(status="error", error=str(exc))
            self.calls.append(record)
            raise
        record.update(status="ok", result=result, version_after=self.store.version)
        self.calls.append(record)
        return result

    # ---- tools ----------------------------------------------------------------------
    def _tool_read_record(self, actor: str, id: str) -> dict:
        if not self.store.exists(id):
            raise ToolError(f"no such record {id!r}")
        return {"id": id, "value": self.store.get(id), "version": self.store.key_version(id)}

    def _tool_update_record(self, actor: str, id: str, field: str, value: Any) -> dict:
        if not self.store.exists(id):
            raise ToolError(f"no such record {id!r}")
        rec = self.store.get(id)
        rec[field] = value
        v = self.store.set(id, rec, actor=actor, step=self.step)
        return {"id": id, "field": field, "value": value, "version": v}

    def _tool_write_file(self, actor: str, path: str, text: str) -> dict:
        target = (self.workspace / path).resolve()
        if self.workspace.resolve() not in target.parents:
            raise ToolError("path escapes workspace")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        return {"path": path, "bytes": len(text.encode())}

    def _tool_issue_refund(self, actor: str, order: str, amount: float) -> dict:
        if amount <= 0:
            raise ToolError("amount must be positive")
        entry = {"order": order, "amount": amount, "actor": actor, "step": self.step,
                 "kind": "refund"}
        self.ledger.append(entry)
        return {"ledger_index": len(self.ledger) - 1, **entry}

    def _tool_send_message(self, actor: str, customer: str, text: str) -> dict:
        entry = {"customer": customer, "text": text, "actor": actor, "step": self.step}
        self.outbox.append(entry)
        return {"outbox_index": len(self.outbox) - 1, **entry}

    # ---- compensation (used by Phase 2, defined now so the semantics are explicit) ----
    def reverse_refund(self, ledger_index: int, actor: str = "recovery") -> dict:
        orig = self.ledger[ledger_index]
        entry = {"order": orig["order"], "amount": -orig["amount"], "actor": actor,
                 "step": self.step, "kind": "reversal", "reverses": ledger_index}
        self.ledger.append(entry)
        return entry
