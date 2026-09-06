"""Memory: short-term conversation history plus a pluggable long-term store.

Short-term memory is a bounded rolling window of `Message`s passed to the LLM
on every turn. Long-term memory is an optional key/value + search-able store
(swap in a real vector DB by implementing `LongTermStore`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class Message:
    """A single turn in a conversation, provider-agnostic."""

    role: Role
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name is not None:
            data["name"] = self.name
        if self.tool_call_id is not None:
            data["tool_call_id"] = self.tool_call_id
        if self.tool_calls is not None:
            data["tool_calls"] = self.tool_calls
        return data


class LongTermStore(Protocol):
    """Implement this against a real vector DB (pgvector, Pinecone, Chroma, ...)
    to give an agent persistent, searchable memory across runs."""

    def add(self, key: str, text: str, metadata: dict[str, Any] | None = None) -> None: ...

    def search(self, query: str, top_k: int = 5) -> list[str]: ...


@dataclass
class InMemoryLongTermStore:
    """Default zero-dependency long-term store: naive substring/keyword search.
    Fine for examples and tests; swap for a real `LongTermStore` in production."""

    _records: dict[str, tuple[str, dict[str, Any]]] = field(default_factory=dict)

    def add(self, key: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        self._records[key] = (text, metadata or {})

    def search(self, query: str, top_k: int = 5) -> list[str]:
        query_terms = {term.lower() for term in query.split() if term}
        scored: list[tuple[int, str]] = []
        for text, _metadata in self._records.values():
            text_lower = text.lower()
            score = sum(1 for term in query_terms if term in text_lower)
            if score > 0:
                scored.append((score, text))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [text for _score, text in scored[:top_k]]


@dataclass
class Memory:
    """Bundles short-term conversation history with an optional long-term store."""

    max_messages: int = 50
    long_term: LongTermStore | None = None
    _messages: list[Message] = field(default_factory=list)

    def add(self, message: Message) -> None:
        self._messages.append(message)
        if len(self._messages) > self.max_messages:
            # Keep the system prompt (if any) plus the most recent window.
            system_messages = [m for m in self._messages if m.role == "system"][:1]
            recent = self._messages[-self.max_messages :]
            self._messages = system_messages + [m for m in recent if m.role != "system"]

    def add_user(self, content: str) -> None:
        self.add(Message(role="user", content=content))

    def add_assistant(self, content: str, tool_calls: list[dict[str, Any]] | None = None) -> None:
        self.add(Message(role="assistant", content=content, tool_calls=tool_calls))

    def add_tool_result(self, tool_call_id: str, name: str, content: str) -> None:
        self.add(Message(role="tool", content=content, name=name, tool_call_id=tool_call_id))

    def history(self) -> list[Message]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    def remember(self, key: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        if self.long_term is None:
            self.long_term = InMemoryLongTermStore()
        self.long_term.add(key, text, metadata)

    def recall(self, query: str, top_k: int = 5) -> list[str]:
        if self.long_term is None:
            return []
        return self.long_term.search(query, top_k=top_k)
