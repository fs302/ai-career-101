from pathlib import Path

from benchmark.scoring import heuristic_scores, weighted_total
from benchmark.storage import BenchmarkStorage
from core.session import SessionStore
from core.types import ToolContext, ToolResult
from tools.base import Tool
from tools.registry import ToolRegistry


class EchoTool(Tool):
    id = "echo"
    name = "Echo"
    description = "Echo test tool"

    def run(self, context: ToolContext, **kwargs):
        return ToolResult(tool_id=self.id, ok=True, content=kwargs.get("text", "ok"))


def test_tool_registry_registers_and_runs():
    registry = ToolRegistry([EchoTool()])
    result = registry.run("echo", ToolContext(role=None, model_router=None), text="hello")
    assert result.ok is True
    assert result.content == "hello"
    assert registry.list_specs()[0]["id"] == "echo"


def test_tool_registry_disabled_error():
    tool = EchoTool()
    tool.enabled = False
    registry = ToolRegistry([tool])
    result = registry.run("echo", ToolContext(role=None, model_router=None))
    assert result.ok is False


def test_session_store_reset_removes_session_roles():
    store = SessionStore()
    store.append_turn("s1", "a", "q", "a")
    store.append_turn("s1", "b", "q", "a")
    store.reset("s1")
    assert store.sessions == {}


def test_benchmark_scoring_and_storage(tmp_path: Path):
    scores = heuristic_scores("下一步检查风险、流程和交付清单", ["风险", "交付"], ["vision.describe"], ["vision.describe"])
    total = weighted_total(scores, {"domain_accuracy": 1.0})
    assert total == scores["domain_accuracy"]

    storage = BenchmarkStorage(runs_dir=tmp_path)
    run = {"run_id": "r1", "created_at": "now", "results": []}
    storage.save_run(run)
    assert storage.load_run("r1")["run_id"] == "r1"
