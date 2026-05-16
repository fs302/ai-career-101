from typing import List, Optional

from careers.prompts import build_system_prompt, build_user_prompt
from careers.roles import CareerRole
from core.session import SessionStore
from core.types import Attachment, ToolContext, WorkflowResult
from llms.router import ModelRouter
from tools.registry import ToolRegistry


class WorkflowEngine:
    def __init__(self, model_router: ModelRouter, tool_registry: ToolRegistry, session_store: SessionStore):
        self.model_router = model_router
        self.tool_registry = tool_registry
        self.session_store = session_store

    def run_chat(
        self,
        role: CareerRole,
        message: str,
        session_id: str,
        attachments: Optional[List[Attachment]] = None,
        text_model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> WorkflowResult:
        attachments = attachments or []
        context = ToolContext(
            role=role,
            model_router=self.model_router,
            attachments=attachments,
            text_model=text_model,
        )
        tool_results = []
        attachment_contexts = []
        used_image = False
        vision_model = None

        for attachment in attachments:
            tool_id = self._tool_for_attachment(role, attachment)
            result = self.tool_registry.run(tool_id, context, attachment=attachment)
            tool_results.append(result)
            if result.ok and result.content:
                attachment_contexts.append(result.content)
            if result.ok and result.tool_id == "vision.describe":
                used_image = True
                vision_model = result.data.get("model") or self.model_router.default_vision_model

        attachment_context = "\n\n".join(attachment_contexts) if attachment_contexts else None
        user_prompt = build_user_prompt(message.strip(), image_context=attachment_context)
        history = self.session_store.get(session_id, role.id)
        messages = [{"role": "system", "content": build_system_prompt(role)}]
        messages.extend(history[-self.session_store.max_messages :])
        messages.append({"role": "user", "content": user_prompt})

        response = self.model_router.chat(messages, model_id=text_model, temperature=0.3, max_tokens=max_tokens)
        self.session_store.append_turn(session_id, role.id, user_prompt, response.content)
        return WorkflowResult(
            answer=response.content,
            text_model=response.model or text_model or self.model_router.default_text_model,
            vision_model=vision_model,
            used_image=used_image,
            attachments=[attachment.filename for attachment in attachments],
            tool_results=tool_results,
        )

    @staticmethod
    def _tool_for_attachment(role: CareerRole, attachment: Attachment) -> str:
        if attachment.kind == "image" and "vision.describe" in role.tools:
            return "vision.describe"
        if attachment.kind == "video":
            return "attachment.video_notice"
        return "attachment.file_notice"
