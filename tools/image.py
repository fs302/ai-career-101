import subprocess
import json
from pathlib import Path
from typing import Optional

from core.types import ToolContext, ToolResult
from tools.base import Tool


GENERATED_DIR = Path(__file__).resolve().parents[1] / "web" / "static" / "generated"


class ImageGenerateTool(Tool):
    id = "image.generate"
    name = "图片生成"
    description = "通过 MiniMax CLI 根据职业任务提示词生成图片。"

    def __init__(self, generated_dir: Path = GENERATED_DIR):
        self.generated_dir = generated_dir

    def run(
        self,
        context: ToolContext,
        prompt: str = "",
        aspect_ratio: str = "16:9",
        out_prefix: Optional[str] = None,
        **_kwargs,
    ) -> ToolResult:
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("prompt is required")

        self.generated_dir.mkdir(parents=True, exist_ok=True)
        prefix = out_prefix or f"career-image-{context.role.id if context.role else 'general'}"
        command = [
            "mmx",
            "image",
            "generate",
            "--prompt",
            prompt,
            "--aspect-ratio",
            aspect_ratio,
            "--out-dir",
            str(self.generated_dir),
            "--out-prefix",
            prefix,
            "--quiet",
            "--non-interactive",
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or "MiniMax image generation failed"
            raise RuntimeError(message)

        image_path = self._parse_saved_path(completed.stdout)
        if image_path is None:
            image_path = self._latest_generated(prefix)
        if image_path is None:
            raise RuntimeError("MiniMax image generation did not return a saved file path")

        image_path = image_path.resolve()
        return ToolResult(
            tool_id=self.id,
            ok=True,
            content=f"/static/generated/{image_path.name}",
            data={
                "image_url": f"/static/generated/{image_path.name}",
                "image_path": str(image_path),
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
            },
        )

    def _parse_saved_path(self, stdout: str) -> Optional[Path]:
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            for raw_path in reversed(data.get("saved", [])):
                path = Path(raw_path)
                if path.exists():
                    return path

        lines = [line.strip().strip('"') for line in stdout.splitlines() if line.strip()]
        for line in reversed(lines):
            path = Path(line)
            if path.exists():
                return path
        return None

    def _latest_generated(self, prefix: str) -> Optional[Path]:
        candidates = sorted(self.generated_dir.glob(f"{prefix}*"), key=lambda path: path.stat().st_mtime, reverse=True)
        return candidates[0] if candidates else None
