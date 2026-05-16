from pathlib import Path

from benchmark.runner import BenchmarkRunner
from benchmark.scoring import heuristic_scores, weighted_total
from benchmark.storage import BenchmarkStorage
from careers.roles import load_roles
from core.session import SessionStore
from core.types import ToolContext, ToolResult
from tools.defaults import build_default_tool_registry
from tools.image import ImageGenerateTool
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


def test_default_registry_includes_image_generation():
    ids = build_default_tool_registry().ids()
    assert "image.generate" in ids


def test_image_generate_tool_parses_saved_file(tmp_path: Path, monkeypatch):
    generated = tmp_path / "test_001.jpg"
    generated.write_bytes(b"fake")

    class Completed:
        returncode = 0
        stdout = f'{{"saved":["{generated}"]}}'
        stderr = ""

    monkeypatch.setattr("tools.image.subprocess.run", lambda *args, **kwargs: Completed())
    tool = ImageGenerateTool(generated_dir=tmp_path)
    result = tool.run(ToolContext(role=None, model_router=None), prompt="a concept image")
    assert result.ok is True
    assert result.data["image_url"] == f"/static/generated/{generated.name}"


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


def test_benchmark_cases_cover_ten_roles_and_registered_tools():
    roles = load_roles()
    registry = build_default_tool_registry()
    runner = BenchmarkRunner(roles=roles, agent_service=None, storage=BenchmarkStorage())
    cases = runner.load_cases()
    by_role = {role_id: [] for role_id in roles}
    for case in cases:
        by_role[case["role_id"]].append(case)
        for tool_id in case.get("required_tools", []):
            assert tool_id in registry.ids()

    assert set(by_role) == set(roles)
    assert all(len(items) >= 3 for items in by_role.values())


def test_benchmark_runner_defaults_to_ten_roles_and_four_models(tmp_path: Path):
    roles = load_roles()

    class FakeService:
        def chat(self, role_id, message, session_id=None, text_model=None, attachments=None):
            from base.career_agent import ChatResult

            return ChatResult(
                session_id=session_id or "s",
                role_id=role_id,
                answer="步骤 清单 风险 下一步 沟通 交付 复盘 建议",
                text_model=text_model or "fake",
                vision_model=None,
                used_image=False,
                attachments=[],
            )

    runner = BenchmarkRunner(roles=roles, agent_service=FakeService(), storage=BenchmarkStorage(runs_dir=tmp_path))
    run = runner.run()
    assert len(run["results"]) == 40
    assert {item["model_id"] for item in run["results"]} == {"minimax-m2.7", "glm-5.1", "qwen3.5-27b", "deepseek-v3.2"}
    assert all("main_failure" in item and "recommended_fix" in item for item in run["results"])

    summary = runner.summary()
    assert summary["models"] == ["minimax-m2.7", "glm-5.1", "qwen3.5-27b", "deepseek-v3.2"]
    assert len(summary["matrix"]) == 10
