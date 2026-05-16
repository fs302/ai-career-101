from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Attachment:
    filename: str
    content_type: str
    content: bytes

    @property
    def kind(self) -> str:
        if self.content_type.startswith("image/"):
            return "image"
        if self.content_type.startswith("video/"):
            return "video"
        if self.content_type.startswith("audio/"):
            return "audio"
        return "file"


@dataclass
class ToolResult:
    tool_id: str
    ok: bool
    content: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class ToolContext:
    role: Any
    model_router: Any
    attachments: List[Attachment] = field(default_factory=list)
    text_model: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowStep:
    id: str
    type: str
    tool: Optional[str] = None
    prompt: Optional[str] = None


@dataclass
class WorkflowResult:
    answer: str
    text_model: str
    vision_model: Optional[str] = None
    used_image: bool = False
    attachments: List[str] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
