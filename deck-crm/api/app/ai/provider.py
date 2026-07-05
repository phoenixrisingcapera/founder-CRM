from __future__ import annotations

from typing import Protocol


class AIProvider(Protocol):
    def complete(self, system: str, user: str) -> dict[str, str]:
        ...
