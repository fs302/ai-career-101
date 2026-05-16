from typing import Dict, Iterable, List

from core.types import ToolContext, ToolResult
from tools.base import Tool


class ToolRegistry:
    def __init__(self, tools: Iterable[Tool] | None = None):
        self._tools: Dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        if tool.id in self._tools:
            raise ValueError(f"Duplicate tool id: {tool.id}")
        self._tools[tool.id] = tool

    def get(self, tool_id: str) -> Tool:
        try:
            return self._tools[tool_id]
        except KeyError as error:
            raise ValueError(f"Unknown tool: {tool_id}") from error

    def run(self, tool_id: str, context: ToolContext, **kwargs) -> ToolResult:
        tool = self.get(tool_id)
        if not tool.enabled:
            return ToolResult(tool_id=tool_id, ok=False, error="Tool is disabled")
        try:
            return tool.run(context, **kwargs)
        except Exception as error:
            return ToolResult(tool_id=tool_id, ok=False, error=str(error))

    def list_specs(self) -> List[dict]:
        return [tool.spec().__dict__ for tool in self._tools.values()]

    def ids(self) -> List[str]:
        return sorted(self._tools)
