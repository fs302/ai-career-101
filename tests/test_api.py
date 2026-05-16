import pytest


class FakeService:
    def __init__(self):
        self.reset_called = None
        self.model_router = FakeModelRouter()
        self.tool_registry = FakeToolRegistry()
        self.roles = {}

    def get_role(self, role_id):
        from careers.roles import CareerRole

        return CareerRole(
            id=role_id,
            name="插画师",
            category="视觉创作",
            tagline="",
            profile="",
            supports_image=True,
            mentor_goal="",
            boundaries=[],
            rules=[],
            workflow=[],
            deliverables=[],
            onboarding_checklist=[],
            scenarios=[],
            starter_questions=[],
            tools=["image.generate"],
            workflows=[],
            artifacts=[],
            benchmark={},
        )

    def list_roles(self):
        return [
            {
                "id": "barista",
                "name": "咖啡师",
                "category": "餐饮服务",
                "tagline": "测试",
                "supports_image": True,
                "starter_questions": ["怎么练习？"],
                "tools": ["vision.describe"],
            }
        ]

    def chat(self, role_id, message, session_id=None, attachments=None, text_model=None, max_tokens=None):
        from base.career_agent import ChatResult

        has_image = any(item[1].startswith("image/") for item in attachments or [])
        return ChatResult(
            session_id=session_id or "new-session",
            role_id=role_id,
            answer=f"answer:{message}",
            text_model=text_model or "fake-text",
            vision_model="fake-vision" if has_image else None,
            used_image=has_image,
            attachments=[item[0] for item in attachments or []],
            used_tools=["vision.describe"] if has_image else [],
        )

    def reset_session(self, session_id):
        self.reset_called = session_id


class FakeSpeechService:
    def translate_to_english_speech(self, source_text, text_model=None):
        from base.minimax_tools import InterpreterSpeechResult

        return InterpreterSpeechResult(
            source_text=source_text,
            translated_text="Hello everyone.",
            audio_url="/static/generated/test.mp3",
            audio_path="/tmp/test.mp3",
        )


class FakeModelRouter:
    def list_models(self):
        return {
            "text": [
                {"id": "minimax-m2.7"},
                {"id": "glm-5.1"},
                {"id": "qwen3.5-27b"},
                {"id": "deepseek-v3.2"},
            ],
            "vision": [{"id": "fake-vision"}],
            "speech": [{"id": "fake-speech"}],
        }


class FakeToolRegistry:
    def list_specs(self):
        return [
            {"id": "vision.describe", "name": "图片理解", "description": "fake", "enabled": True},
            {"id": "image.generate", "name": "图片生成", "description": "fake", "enabled": True},
        ]

    def run(self, tool_id, context, **kwargs):
        from core.types import ToolResult

        if tool_id == "image.generate":
            return ToolResult(
                tool_id=tool_id,
                ok=True,
                content="/static/generated/fake.jpg",
                data={
                    "image_url": "/static/generated/fake.jpg",
                    "image_path": "/tmp/fake.jpg",
                    "prompt": kwargs["prompt"],
                    "aspect_ratio": kwargs["aspect_ratio"],
                },
            )
        return ToolResult(tool_id=tool_id, ok=False, error="unexpected")


class FakeBenchmarkRunner:
    def summary(self):
        return {
            "runs": [],
            "models": ["MiniMax-M2.7"],
            "matrix": [
                {
                    "role_id": "barista",
                    "role_name": "咖啡师",
                    "models": {"MiniMax-M2.7": None},
                    "latest_completion": None,
                    "tool_use_score": None,
                    "safety_score": None,
                    "main_failure": "尚未运行",
                    "recommended_fix": "运行动态 Benchmark 后生成建议。",
                }
            ],
        }

    def run(self, role_ids=None, model_ids=None, case_ids=None, case_limit_per_role=None, use_llm_judge=True):
        return {"run_id": "run1", "created_at": "now", "results": []}

    def generate_outputs(self, role_ids=None, model_ids=None, case_ids=None, case_limit_per_role=None, progress_callback=None):
        return {"run_id": "gen1", "status": "generated", "total_outputs": 10, "config": {}}

    def evaluate_outputs(self, run_id=None, judge_model_id="glm-5.1", use_llm_judge=True, progress_callback=None):
        return {"run_id": run_id, "status": "completed", "judge_model": judge_model_id, "total_evaluated": 10, "results_count": 4}

    def get_run_status(self, run_id):
        return {
            "run_id": run_id,
            "status": "completed",
            "config": {},
            "judge_model": "glm-5.1",
            "created_at": "now",
            "outputs_generated_at": "now",
            "evaluated_at": "now",
            "outputs_count": 10,
            "evaluated_count": 10,
            "roles": ["barista"],
            "models": ["minimax-m2.7"],
        }

    def get_run(self, run_id):
        return {"run_id": run_id, "results": []}


@pytest.fixture()
def client(monkeypatch):
    fastapi = pytest.importorskip("fastapi")
    pytest.importorskip("multipart")
    from fastapi.testclient import TestClient
    from web.app import AppContainer, create_app

    app = create_app(AppContainer(FakeService(), FakeSpeechService(), FakeBenchmarkRunner()))
    return TestClient(app)


def test_roles_endpoint(client):
    response = client.get("/api/roles")
    assert response.status_code == 200
    assert response.json()["roles"][0]["id"] == "barista"


def test_chat_endpoint(client):
    response = client.post(
        "/api/chat",
        data={"role_id": "barista", "message": "hello", "session_id": "s1", "text_model": "deepseek-reasoner"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "answer:hello"
    assert data["session_id"] == "s1"
    assert data["text_model"] == "deepseek-reasoner"


def test_chat_endpoint_with_multiple_files(client):
    response = client.post(
        "/api/chat",
        data={"role_id": "barista", "message": "hello"},
        files=[
            ("files", ("coffee.png", b"image", "image/png")),
            ("files", ("clip.mp4", b"video", "video/mp4")),
        ],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["used_image"] is True
    assert data["attachments"] == ["coffee.png", "clip.mp4"]


def test_reset_endpoint(client):
    response = client.post("/api/sessions/s1/reset")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_interpreter_translate_speech_endpoint(client):
    response = client.post(
        "/api/interpreter/translate-speech",
        data={"source_text": "大家好。", "text_model": "minimax-m2.7"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["translated_text"] == "Hello everyone."
    assert data["audio_url"].endswith(".mp3")


def test_models_and_tools_endpoints(client):
    model_ids = [item["id"] for item in client.get("/api/models").json()["text"]]
    assert model_ids == ["minimax-m2.7", "glm-5.1", "qwen3.5-27b", "deepseek-v3.2"]
    assert client.get("/api/tools").json()["tools"][0]["id"] == "vision.describe"


def test_image_generate_endpoint(client):
    response = client.post(
        "/api/tools/image-generate",
        data={"role_id": "illustrator", "prompt": "生成一张角色概念图", "aspect_ratio": "16:9"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["image_url"] == "/static/generated/fake.jpg"
    assert data["prompt"] == "生成一张角色概念图"


def test_benchmark_endpoints(client):
    summary = client.get("/api/benchmark/summary")
    assert summary.status_code == 200
    assert summary.json()["matrix"][0]["role_id"] == "barista"
    assert summary.json()["models"] == ["MiniMax-M2.7"]
    run = client.post("/api/benchmark/run", json={})
    assert run.status_code == 200
    assert run.json()["run_id"] == "run1"
    detail = client.get("/api/benchmark/runs/run1")
    assert detail.status_code == 200


def test_benchmark_generate_endpoint(client):
    response = client.post("/api/benchmark/generate", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == "gen1"
    assert data["status"] == "generated"
    assert data["total_outputs"] == 10


def test_benchmark_evaluate_endpoint(client):
    response = client.post("/api/benchmark/evaluate?run_id=gen1&judge_model=glm-5.1&use_llm_judge=true")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == "gen1"
    assert data["status"] == "completed"
    assert data["judge_model"] == "glm-5.1"


def test_benchmark_status_endpoint(client):
    response = client.get("/api/benchmark/status/gen1")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == "gen1"
    assert data["status"] == "completed"
    assert data["outputs_count"] == 10
    assert data["evaluated_count"] == 10
