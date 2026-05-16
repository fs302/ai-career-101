from dataclasses import dataclass
from typing import List, Optional, Tuple
from uuid import uuid4

from agents.workflow_engine import WorkflowEngine
from careers.roles import CareerRole, load_roles
from commons.env import load_dotenv
from core.session import SessionStore
from core.types import Attachment
from llms.router import ModelRouter
from tools.defaults import build_default_tool_registry
from tools.registry import ToolRegistry


@dataclass
class ChatResult:
    session_id: str
    role_id: str
    answer: str
    text_model: str
    vision_model: Optional[str]
    used_image: bool
    attachments: List[str]


class CareerAgentService:
    def __init__(
        self,
        provider_name: str = "sjtu",
        model_router: Optional[ModelRouter] = None,
        tool_registry: Optional[ToolRegistry] = None,
        session_store: Optional[SessionStore] = None,
    ):
        load_dotenv()
        self.roles = load_roles()
        self.model_router = model_router or ModelRouter(provider_name=provider_name)
        self.tool_registry = tool_registry or build_default_tool_registry()
        self.session_store = session_store or SessionStore()
        self.workflow_engine = WorkflowEngine(self.model_router, self.tool_registry, self.session_store)

    def list_roles(self) -> List[dict]:
        return [role.to_public_dict() for role in self.roles.values()]

    def get_role(self, role_id: str) -> CareerRole:
        try:
            return self.roles[role_id]
        except KeyError as error:
            raise ValueError(f"Unknown role_id: {role_id}") from error

    def chat(
        self,
        role_id: str,
        message: str,
        session_id: Optional[str] = None,
        attachments: Optional[List[Tuple[str, str, bytes]]] = None,
        text_model: Optional[str] = None,
    ) -> ChatResult:
        role = self.get_role(role_id)
        if not message.strip():
            raise ValueError("message is required")

        session_id = session_id or uuid4().hex
        normalized_attachments = [
            Attachment(filename=filename, content_type=content_type or "", content=content)
            for filename, content_type, content in attachments or []
        ]
        result = self.workflow_engine.run_chat(
            role=role,
            message=message.strip(),
            session_id=session_id,
            attachments=normalized_attachments,
            text_model=text_model,
        )

        return ChatResult(
            session_id=session_id,
            role_id=role.id,
            answer=result.answer,
            text_model=result.text_model,
            vision_model=result.vision_model,
            used_image=result.used_image,
            attachments=result.attachments,
        )

    def reset_session(self, session_id: str) -> None:
        self.session_store.reset(session_id)

    @property
    def sessions(self) -> dict:
        return self.session_store.sessions
