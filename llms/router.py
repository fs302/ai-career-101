import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from llms.base import Message, ModelResponse
from llms.openai_compatible import OpenAICompatibleChatModel, OpenAICompatibleVisionModel
from llms.providers import LLMProvider, get_provider
from benchmark.config import DEFAULT_BENCHMARK_MODELS, MODEL_DISPLAY_NAMES


@dataclass(frozen=True)
class ModelInfo:
    id: str
    name: str
    provider: str
    modality: str
    default: bool = False


class ModelRouter:
    """Stateless model router. Each call creates an isolated model client."""

    def __init__(self, provider_name: str = "sjtu"):
        self.provider: LLMProvider = get_provider(provider_name)

    @property
    def provider_name(self) -> str:
        return self.provider.name

    @property
    def default_text_model(self) -> str:
        return os.environ.get(self.provider.text_model_env or "", "") or self.provider.default_text_model

    @property
    def default_vision_model(self) -> Optional[str]:
        env_name = self.provider.vision_model_env
        return (os.environ.get(env_name) if env_name else None) or self.provider.default_vision_model

    def text_client(self, model_id: Optional[str] = None) -> OpenAICompatibleChatModel:
        return OpenAICompatibleChatModel(provider=self.provider, model=model_id or self.default_text_model)

    def vision_client(self, model_id: Optional[str] = None) -> OpenAICompatibleVisionModel:
        return OpenAICompatibleVisionModel(provider=self.provider, model=model_id or self.default_vision_model)

    def chat(
        self,
        messages: Sequence[Message],
        model_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ModelResponse:
        return self.text_client(model_id).chat(messages, temperature=temperature, max_tokens=max_tokens)

    def invoke(self, prompt: str, model_id: Optional[str] = None, **kwargs) -> str:
        return self.text_client(model_id).invoke(prompt, **kwargs)

    def describe_image(self, image_path: str, prompt: str, model_id: Optional[str] = None) -> ModelResponse:
        return self.vision_client(model_id).describe_image(image_path, prompt=prompt)

    def list_models(self) -> Dict[str, List[dict]]:
        text_models = [
            ModelInfo(model_id, MODEL_DISPLAY_NAMES[model_id], self.provider.name, "text", self.default_text_model == model_id)
            for model_id in DEFAULT_BENCHMARK_MODELS
        ]
        vision_models = [
            ModelInfo(self.default_vision_model or "qwen", self.default_vision_model or "qwen", self.provider.name, "vision", True)
        ]
        speech_models = [
            ModelInfo("speech-2.8-hd", "MiniMax speech-2.8-hd", "minimax-cli", "speech", True)
        ]
        return {
            "text": [item.__dict__ for item in text_models],
            "vision": [item.__dict__ for item in vision_models],
            "speech": [item.__dict__ for item in speech_models],
        }
