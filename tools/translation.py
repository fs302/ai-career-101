from core.types import ToolContext, ToolResult
from tools.base import Tool


class ZhEnTranslationTool(Tool):
    id = "translation.zh_en"
    name = "中文到英文口译翻译"
    description = "把中文转换成适合现场口译或字幕场景的自然英文。"

    def run(self, context: ToolContext, source_text: str = "", style: str = "interpretation", **_kwargs) -> ToolResult:
        source_text = source_text.strip()
        if not source_text:
            raise ValueError("source_text is required")

        if style == "subtitle":
            instruction = "请把下面中文转换成自然英文字幕，只输出英文译文，要求口语、简洁、适合屏幕阅读。"
        else:
            instruction = (
                "你是同声传译师。请把下面中文转换成适合现场口译的自然英文，只输出英文译文，"
                "不要解释，不要添加标题。要求简洁、口语、保留关键信息和语气。"
            )
        translated = context.model_router.invoke(
            f"{instruction}\n\n中文：{source_text}",
            model_id=context.text_model,
            temperature=0.2,
        ).strip()
        return ToolResult(
            tool_id=self.id,
            ok=True,
            content=translated,
            data={"source_text": source_text, "target_language": "en"},
        )
