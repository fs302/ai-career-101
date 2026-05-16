from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class LLMProvider:
    name: str
    base_url: str
    api_key_env: str
    default_text_model: str
    default_vision_model: Optional[str] = None
    base_url_env: Optional[str] = None
    text_model_env: Optional[str] = None
    vision_model_env: Optional[str] = None


MINIMAX_PROVIDER = LLMProvider(
    name="minimax",
    base_url="https://api.minimax.chat/v1",
    api_key_env="MINIMAX_API_KEY",
    default_text_model="MiniMax-M2.7",
    base_url_env="MINIMAX_BASE_URL",
    text_model_env="MINIMAX_TEXT_MODEL",
)


SJTU_PROVIDER = LLMProvider(
    name="sjtu",
    base_url="https://models.sjtu.edu.cn/api/v1",
    api_key_env="SJTU_API_KEY",
    default_text_model="minimax-m2.7",
    default_vision_model="qwen",
    base_url_env="SJTU_BASE_URL",
    text_model_env="SJTU_TEXT_MODEL",
    vision_model_env="SJTU_VISION_MODEL",
)


PROVIDERS: Dict[str, LLMProvider] = {
    MINIMAX_PROVIDER.name: MINIMAX_PROVIDER,
    SJTU_PROVIDER.name: SJTU_PROVIDER,
}


def get_provider(name: str) -> LLMProvider:
    try:
        return PROVIDERS[name]
    except KeyError as error:
        available = ", ".join(sorted(PROVIDERS))
        raise ValueError(f"Unknown LLM provider '{name}'. Available providers: {available}") from error
