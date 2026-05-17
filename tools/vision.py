from pathlib import Path
from tempfile import NamedTemporaryFile

from core.types import Attachment, ToolContext, ToolResult
from tools.base import Tool


class VisionDescribeTool(Tool):
    id = "vision.describe"
    name = "图片理解"
    description = "使用视觉模型描述图片中与职业任务相关的可见信息。"

    def run(self, context: ToolContext, attachment: Attachment | None = None, **_kwargs) -> ToolResult:
        image = attachment or next((item for item in context.attachments if item.kind == "image"), None)
        if image is None:
            raise ValueError("image attachment is required")

        suffix = Path(image.filename).suffix or ".png"
        prompt = (
            f"你正在辅助「{context.role.name}」职业导师理解用户上传的图片。"
            "请用中文描述与职业任务相关的可见信息，避免过度推断。"
        )

        # Keep temp file alive until describe_image completes
        with NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_file.write(image.content)
            temp_file.flush()
            temp_path = temp_file.name

        try:
            response = context.model_router.describe_image(temp_path, prompt=prompt)
            return ToolResult(
                tool_id=self.id,
                ok=True,
                content=response.content,
                data={"filename": image.filename, "model": response.model},
            )
        finally:
            # Clean up temp file after use
            Path(temp_path).unlink(missing_ok=True)
