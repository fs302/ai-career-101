from tools.attachment import FileNoticeTool, VideoNoticeTool
from tools.registry import ToolRegistry
from tools.speech import SpeechTtsTool
from tools.translation import ZhEnTranslationTool
from tools.vision import VisionDescribeTool


def build_default_tool_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            VisionDescribeTool(),
            VideoNoticeTool(),
            FileNoticeTool(),
            ZhEnTranslationTool(),
            SpeechTtsTool(),
        ]
    )
