from io import BytesIO
from pathlib import Path

from PIL import Image

from core.types import Attachment, ToolContext, ToolResult
from tools.base import Tool


class VisionDescribeTool(Tool):
    id = "vision.describe"
    name = "图片理解"
    description = "使用视觉模型描述图片中与职业任务相关的可见信息。"

    # Vision model works well with images up to ~200KB; max dimension 1024px
    MAX_DIMENSION = 1024
    JPEG_QUALITY = 80

    @staticmethod
    def _compress_image(content: bytes) -> bytes:
        """Compress image to reduce vision model latency."""
        img = Image.open(BytesIO(content))
        # Convert RGBA/PALETTE to RGB for JPEG compatibility
        if img.mode in ("RGBA", "P", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Downscale if needed (maintain aspect ratio)
        w, h = img.size
        if w > VisionDescribeTool.MAX_DIMENSION or h > VisionDescribeTool.MAX_DIMENSION:
            ratio = VisionDescribeTool.MAX_DIMENSION / max(w, h)
            new_w = int(w * ratio)
            new_h = int(h * ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)

        # Save as compressed JPEG
        output = BytesIO()
        img.save(output, format="JPEG", quality=VisionDescribeTool.JPEG_QUALITY, optimize=True)
        return output.getvalue()

    def run(self, context: ToolContext, attachment: Attachment | None = None, **_kwargs) -> ToolResult:
        image = attachment or next((item for item in context.attachments if item.kind == "image"), None)
        if image is None:
            raise ValueError("image attachment is required")

        original_size = len(image.content)
        compressed = self._compress_image(image.content)
        compressed_size = len(compressed)

        prompt = (
            f"你正在辅助「{context.role.name}」职业导师理解用户上传的图片。"
            "请用中文描述与职业任务相关的可见信息，避免过度推断。"
        )

        # Write compressed image to temp file
        with Path("/tmp").joinpath(f"vision_{Path(image.filename).stem}.jpg").open("wb") as temp_file:
            temp_file.write(compressed)
            temp_path = str(temp_file.parent / temp_file.name)

        try:
            response = context.model_router.describe_image(temp_path, prompt=prompt)
            return ToolResult(
                tool_id=self.id,
                ok=True,
                content=response.content,
                data={
                    "filename": image.filename,
                    "model": response.model,
                    "original_size": original_size,
                    "compressed_size": compressed_size,
                },
            )
        finally:
            Path(temp_path).unlink(missing_ok=True)
