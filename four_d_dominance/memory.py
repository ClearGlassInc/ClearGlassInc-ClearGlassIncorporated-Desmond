"""Memory layer: short-term working buffer + long-term key/value store.

Backed by JSON so context persists across pipeline runs (the "memory
components for context persistence" gap called out in the strategy doc).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Memory:
    short_term: list[dict[str, Any]] = field(default_factory=list)
    long_term: dict[str, Any] = field(default_factory=dict)
    max_short_term: int = 50

    def remember(self, event: dict[str, Any]) -> None:
        """Append an event to the working buffer, trimming the oldest entries."""
        self.short_term.append(event)
        if len(self.short_term) > self.max_short_term:
            self.short_term = self.short_term[-self.max_short_term :]

    def learn(self, key: str, value: Any) -> None:
        self.long_term[key] = value

    def recall(self, key: str, default: Any = None) -> Any:
        return self.long_term.get(key, default)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Memory:
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            short_term=data.get("short_term", []),
            long_term=data.get("long_term", {}),
            max_short_term=data.get("max_short_term", 50),
        )
