from dataclasses import dataclass, field
from typing import Protocol

HISTORY_LIMIT = 5


@dataclass
class ConversationContext:
    history: list[dict] = field(default_factory=list)
    pending_escalation: bool = False


class ConversationStore(Protocol):
    def load(self, session_id: str) -> ConversationContext: ...
    def save(self, session_id: str, context: ConversationContext) -> None: ...


class InMemoryConversationStore:
    def __init__(self) -> None:
        self._data: dict[str, ConversationContext] = {}

    def load(self, session_id: str) -> ConversationContext:
        if session_id not in self._data:
            self._data[session_id] = ConversationContext(history=[], pending_escalation=False)
        return self._data[session_id]

    def save(self, session_id: str, context: ConversationContext) -> None:
        self._data[session_id] = context
