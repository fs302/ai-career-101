from dataclasses import dataclass

from base.career_agent import CareerAgentService
from core.session import SessionStore
from llms.router import ModelRouter
from tools.defaults import build_default_tool_registry


@dataclass
class FakeResponse:
    content: str
    model: str = "fake"
    raw: dict = None


class FakeModelRouter:
    def __init__(self):
        self.messages = []
        self.text_model_ids = []
        self.default_text_model = "fake-text"
        self.default_vision_model = "fake-vision"

    def chat(self, messages, model_id=None, temperature=None, max_tokens=None):
        self.messages.append(messages)
        self.text_model_ids.append(model_id)
        return FakeResponse(content="导师回复", model=model_id or "fake-text")

    def describe_image(self, image_path, prompt="Describe this image.", temperature=None, max_tokens=None):
        return FakeResponse(content="图片里有一杯咖啡", model="fake-vision")

    def list_models(self):
        return {"text": [], "vision": [], "speech": []}


def make_service():
    return CareerAgentService(
        model_router=FakeModelRouter(),
        tool_registry=build_default_tool_registry(),
        session_store=SessionStore(),
    )


def test_chat_records_history():
    service = make_service()
    result = service.chat("barista", "新人第一周练什么？", session_id="s1")
    assert result.answer == "导师回复"
    assert result.session_id == "s1"
    assert len(service.sessions[("s1", "barista")]) == 2


def test_chat_supports_text_model_override():
    service = make_service()
    result = service.chat("barista", "新人第一周练什么？", session_id="s1", text_model="deepseek-reasoner")
    assert result.text_model == "deepseek-reasoner"
    assert service.model_router.text_model_ids == ["deepseek-reasoner"]


def test_chat_includes_image_context():
    service = make_service()
    result = service.chat(
        "barista",
        "帮我看出品问题",
        session_id="s2",
        attachments=[("coffee.png", "image/png", b"fake-image")],
    )
    assert result.used_image is True
    assert result.vision_model == "fake-vision"
    sent_messages = service.model_router.messages[-1]
    assert "图片里有一杯咖啡" in sent_messages[-1]["content"]


def test_chat_includes_video_attachment_notice():
    service = make_service()
    result = service.chat(
        "game_designer",
        "这个视频能怎么做新手引导？",
        session_id="s3",
        attachments=[("clip.mp4", "video/mp4", b"fake-video")],
    )
    assert result.used_image is False
    assert result.attachments == ["clip.mp4"]
    sent_messages = service.model_router.messages[-1]
    assert "尚未解析视频内容" in sent_messages[-1]["content"]


def test_model_router_override_does_not_mutate_shared_state(monkeypatch):
    created_models = []

    class FakeClient:
        def __init__(self, provider, model=None):
            self.model = model
            created_models.append(model)

        def chat(self, messages, temperature=None, max_tokens=None):
            return FakeResponse(content="ok", model=self.model)

    monkeypatch.setattr("llms.router.OpenAICompatibleChatModel", FakeClient)
    router = ModelRouter(provider_name="sjtu")
    router.chat([{"role": "user", "content": "a"}], model_id="m1")
    router.chat([{"role": "user", "content": "b"}], model_id="m2")
    assert created_models == ["m1", "m2"]


def test_reset_session_removes_all_roles_for_session():
    service = make_service()
    service.chat("barista", "问题1", session_id="same")
    service.chat("nutritionist", "问题2", session_id="same")
    service.reset_session("same")
    assert service.sessions == {}
