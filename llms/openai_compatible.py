import base64
import json
import mimetypes
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Sequence

from llms.base import Message, ModelResponse, TextModel, VisionModel
from llms.providers import LLMProvider


class LLMProviderError(RuntimeError):
    pass


class OpenAICompatibleChatModel(TextModel):
    def __init__(
        self,
        provider: LLMProvider,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 600,
        retries: int = 3,
    ):
        self.provider = provider
        self.api_key = api_key or os.environ.get(provider.api_key_env)
        if not self.api_key:
            raise ValueError(f"{provider.api_key_env} is required for provider '{provider.name}'.")

        env_base_url = os.environ.get(provider.base_url_env) if provider.base_url_env else None
        env_text_model = os.environ.get(provider.text_model_env) if provider.text_model_env else None
        self.base_url = (base_url or env_base_url or provider.base_url).rstrip("/")
        self.model = model or env_text_model or provider.default_text_model
        self.timeout = timeout
        self.retries = retries

    def chat(
        self,
        messages: Sequence[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ModelResponse:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": list(messages),
            "stream": False,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        data = self._post("/chat/completions", payload)
        content = _clean_model_content(data["choices"][0]["message"]["content"])
        return ModelResponse(content=content, model=data.get("model", self.model), raw=data)

    def list_models(self) -> Dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}/models",
            headers={"Authorization": f"Bearer {self.api_key}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise LLMProviderError(f"{self.provider.name} API HTTP {error.code}: {body}") from error
        except urllib.error.URLError as error:
            raise LLMProviderError(f"{self.provider.name} API request failed: {error.reason}") from error

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        last_error: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                body = error.read().decode("utf-8", errors="replace")
                if 400 <= error.code < 500 and error.code != 429:
                    raise LLMProviderError(f"{self.provider.name} API HTTP {error.code}: {body}") from error
                last_error = LLMProviderError(f"{self.provider.name} API HTTP {error.code}: {body}")
            except urllib.error.URLError as error:
                last_error = LLMProviderError(f"{self.provider.name} API request failed: {error.reason}")

            if attempt < self.retries:
                time.sleep(2)

        raise LLMProviderError(f"{self.provider.name} API request failed after retries.") from last_error


class OpenAICompatibleVisionModel(OpenAICompatibleChatModel, VisionModel):
    def __init__(
        self,
        provider: LLMProvider,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 600,
        retries: int = 3,
    ):
        env_vision_model = os.environ.get(provider.vision_model_env) if provider.vision_model_env else None
        default_vision_model = env_vision_model or provider.default_vision_model
        if model is None and default_vision_model is None:
            raise ValueError(f"Provider '{provider.name}' does not define a default vision model.")
        super().__init__(
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            model=model or default_vision_model,
            timeout=timeout,
            retries=retries,
        )

    def describe_image(
        self,
        image_path: str,
        prompt: str = "Describe this image.",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ModelResponse:
        mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
        with open(image_path, "rb") as image_file:
            image_base64 = base64.b64encode(image_file.read()).decode("ascii")

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_base64}",
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        return self.chat(messages, temperature=temperature, max_tokens=max_tokens)


def _clean_model_content(content: str) -> str:
    return re.sub(r"^\s*<think>.*?</think>\s*", "", content, flags=re.DOTALL).strip()
