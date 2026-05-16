from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from core.types import ToolContext, ToolResult


@dataclass(frozen=True)
class ToolSpec:
    id: str
    name: str
    description: str
    enabled: bool = True


class Tool(ABC):
    id: str
    name: str
    description: str
    enabled: bool = True

    def spec(self) -> ToolSpec:
        return ToolSpec(
            id=self.id,
            name=self.name,
            description=self.description,
            enabled=self.enabled,
        )

    @abstractmethod
    def run(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        pass
