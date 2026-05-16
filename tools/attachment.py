from core.types import Attachment, ToolContext, ToolResult
from tools.base import Tool


class VideoNoticeTool(Tool):
    id = "attachment.video_notice"
    name = "视频附件提示"
    description = "记录视频已上传，并提示当前版本尚未解析视频内容。"

    def run(self, context: ToolContext, attachment: Attachment | None = None, **_kwargs) -> ToolResult:
        video = attachment or next((item for item in context.attachments if item.kind == "video"), None)
        if video is None:
            raise ValueError("video attachment is required")
        return ToolResult(
            tool_id=self.id,
            ok=True,
            content=f"用户上传了视频附件「{video.filename}」。当前版本尚未解析视频内容，只能基于用户文字说明提供建议。",
            data={"filename": video.filename, "content_type": video.content_type},
        )


class FileNoticeTool(Tool):
    id = "attachment.file_notice"
    name = "通用附件提示"
    description = "记录非图片/视频附件的文件名和类型。"

    def run(self, context: ToolContext, attachment: Attachment | None = None, **_kwargs) -> ToolResult:
        file = attachment or next((item for item in context.attachments if item.kind == "file"), None)
        if file is None:
            raise ValueError("file attachment is required")
        content_type = file.content_type or "unknown"
        return ToolResult(
            tool_id=self.id,
            ok=True,
            content=f"用户上传了附件「{file.filename}」，类型为 {content_type}。",
            data={"filename": file.filename, "content_type": content_type},
        )
