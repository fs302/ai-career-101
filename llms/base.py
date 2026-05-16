from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Union


MessageContent = Union[str, List[Dict[str, Any]]]
Message = Dict[str, MessageContent]


@dataclass
class ModelResponse:
    content: str
    model: str
    raw: Dict[str, Any]


class TextModel(ABC):
    @abstractmethod
    def chat(
        self,
        messages: Sequence[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ModelResponse:
        pass

    def invoke(self, prompt: str, **kwargs: Any) -> str:
        response = self.chat([{"role": "user", "content": prompt}], **kwargs)
        return response.content


class VisionModel(ABC):
    @abstractmethod
    def describe_image(
        self,
        image_path: str,
        prompt: str = "Describe this image.",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ModelResponse:
        pass
