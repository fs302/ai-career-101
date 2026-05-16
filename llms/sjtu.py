from llms.openai_compatible import LLMProviderError, OpenAICompatibleChatModel, OpenAICompatibleVisionModel
from llms.providers import SJTU_PROVIDER


SJTUAPIError = LLMProviderError
DEFAULT_TEXT_MODEL = SJTU_PROVIDER.default_text_model
DEFAULT_VISION_MODEL = SJTU_PROVIDER.default_vision_model


class SJTUChatModel(OpenAICompatibleChatModel):
    def __init__(self, *args, **kwargs):
        super().__init__(SJTU_PROVIDER, *args, **kwargs)


class SJTUVisionModel(OpenAICompatibleVisionModel):
    def __init__(self, *args, **kwargs):
        super().__init__(SJTU_PROVIDER, *args, **kwargs)
