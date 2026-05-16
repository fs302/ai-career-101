from dataclasses import dataclass

from careers.roles import CareerRole
from core.types import ToolContext
from llms.router import ModelRouter
from tools.registry import ToolRegistry


@dataclass
class InterpreterSpeechResult:
    source_text: str
    translated_text: str
    audio_url: str
    audio_path: str


class InterpreterSpeechService:
    """Compatibility wrapper around the generic translation and TTS tools."""

    def __init__(self, model_router: ModelRouter, tool_registry: ToolRegistry):
        self.model_router = model_router
        self.tool_registry = tool_registry

    def translate_to_english_speech(self, source_text: str, text_model: str | None = None) -> InterpreterSpeechResult:
        source_text = source_text.strip()
        if not source_text:
            raise ValueError("source_text is required")

        role = CareerRole(
            id="interpreter",
            name="同声传译师",
            category="语言与会议",
            tagline="",
            profile="",
            supports_image=False,
            mentor_goal="",
            boundaries=[],
            rules=[],
            workflow=[],
            deliverables=[],
            onboarding_checklist=[],
            scenarios=[],
            starter_questions=[],
            tools=["translation.zh_en", "speech.tts"],
            workflows=[],
            artifacts=[],
            benchmark={},
        )
        context = ToolContext(role=role, model_router=self.model_router, text_model=text_model)
        translation = self.tool_registry.run("translation.zh_en", context, source_text=source_text)
        if not translation.ok:
            raise RuntimeError(translation.error or "Translation failed")
        speech = self.tool_registry.run("speech.tts", context, text=translation.content)
        if not speech.ok:
            raise RuntimeError(speech.error or "Speech synthesis failed")
        return InterpreterSpeechResult(
            source_text=source_text,
            translated_text=translation.content,
            audio_url=speech.data["audio_url"],
            audio_path=speech.data["audio_path"],
        )
