import subprocess
from pathlib import Path
from uuid import uuid4

from core.types import ToolContext, ToolResult
from tools.base import Tool


GENERATED_DIR = Path(__file__).resolve().parents[1] / "web" / "static" / "generated"


class SpeechTtsTool(Tool):
    id = "speech.tts"
    name = "语音合成"
    description = "通过 MiniMax CLI 将文本合成为音频文件。"

    def __init__(self, generated_dir: Path = GENERATED_DIR):
        self.generated_dir = generated_dir

    def run(
        self,
        context: ToolContext,
        text: str = "",
        voice: str = "English_expressive_narrator",
        language: str = "English",
        **_kwargs,
    ) -> ToolResult:
        text = text.strip()
        if not text:
            raise ValueError("text is required")

        self.generated_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.generated_dir / f"speech-{uuid4().hex}.mp3"
        command = [
            "mmx",
            "speech",
            "synthesize",
            "--text",
            text,
            "--voice",
            voice,
            "--language",
            language,
            "--out",
            str(output_path),
            "--quiet",
            "--non-interactive",
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or "MiniMax speech synthesis failed"
            raise RuntimeError(message)

        return ToolResult(
            tool_id=self.id,
            ok=True,
            content=f"/static/generated/{output_path.name}",
            data={"audio_url": f"/static/generated/{output_path.name}", "audio_path": str(output_path)},
        )
