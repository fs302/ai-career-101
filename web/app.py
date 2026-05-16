from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from base.career_agent import CareerAgentService
from base.minimax_tools import InterpreterSpeechService
from benchmark.runner import BenchmarkRunner
from benchmark.storage import BenchmarkStorage
from commons.env import load_dotenv
from core.types import ToolContext


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"


class AppContainer:
    def __init__(
        self,
        agent_service: Optional[CareerAgentService] = None,
        speech_service: Optional[InterpreterSpeechService] = None,
        benchmark_runner: Optional[BenchmarkRunner] = None,
    ):
        load_dotenv()
        self._agent_service = agent_service
        self._speech_service = speech_service
        self._benchmark_runner = benchmark_runner

    @property
    def agent_service(self) -> CareerAgentService:
        if self._agent_service is None:
            self._agent_service = CareerAgentService()
        return self._agent_service

    @property
    def speech_service(self) -> InterpreterSpeechService:
        if self._speech_service is None:
            self._speech_service = InterpreterSpeechService(
                self.agent_service.model_router,
                self.agent_service.tool_registry,
            )
        return self._speech_service

    @property
    def benchmark_runner(self) -> BenchmarkRunner:
        if self._benchmark_runner is None:
            self._benchmark_runner = BenchmarkRunner(
                roles=self.agent_service.roles,
                agent_service=self.agent_service,
                storage=BenchmarkStorage(),
            )
        return self._benchmark_runner


def create_app(container: Optional[AppContainer] = None) -> FastAPI:
    container = container or AppContainer()
    app = FastAPI(title="AI-Career-101")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return (STATIC_DIR / "home.html").read_text(encoding="utf-8")

    @app.get("/chat", response_class=HTMLResponse)
    def chat_page() -> str:
        return (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    @app.get("/benchmark", response_class=HTMLResponse)
    def benchmark_page() -> str:
        return (STATIC_DIR / "benchmark.html").read_text(encoding="utf-8")

    @app.get("/api/roles")
    def list_roles() -> dict:
        return {"roles": container.agent_service.list_roles()}

    @app.get("/api/models")
    def list_models() -> dict:
        return container.agent_service.model_router.list_models()

    @app.get("/api/tools")
    def list_tools() -> dict:
        return {"tools": container.agent_service.tool_registry.list_specs()}

    @app.post("/api/chat")
    async def chat(
        role_id: str = Form(...),
        message: str = Form(...),
        session_id: Optional[str] = Form(None),
        text_model: Optional[str] = Form(None),
        files: Optional[List[UploadFile]] = File(None),
    ) -> dict:
        attachments = []
        for upload in files or []:
            content = await upload.read()
            if content:
                attachments.append((upload.filename or "upload", upload.content_type or "", content))

        try:
            result = container.agent_service.chat(
                role_id=role_id,
                message=message,
                session_id=session_id,
                attachments=attachments,
                text_model=text_model,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"LLM request failed: {error}") from error

        return {
            "session_id": result.session_id,
            "role_id": result.role_id,
            "answer": result.answer,
            "text_model": result.text_model,
            "vision_model": result.vision_model,
            "used_image": result.used_image,
            "attachments": result.attachments,
        }

    @app.post("/api/sessions/{session_id}/reset")
    def reset_session(session_id: str) -> dict:
        container.agent_service.reset_session(session_id)
        return {"ok": True, "session_id": session_id}

    @app.post("/api/interpreter/translate-speech")
    def translate_speech(source_text: str = Form(...), text_model: Optional[str] = Form(None)) -> dict:
        try:
            result = container.speech_service.translate_to_english_speech(source_text, text_model=text_model)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"MiniMax speech request failed: {error}") from error

        return {
            "source_text": result.source_text,
            "translated_text": result.translated_text,
            "audio_url": result.audio_url,
            "audio_path": result.audio_path,
        }

    @app.post("/api/tools/image-generate")
    def generate_image(
        role_id: str = Form("illustrator"),
        prompt: str = Form(...),
        aspect_ratio: str = Form("16:9"),
    ) -> dict:
        try:
            role = container.agent_service.get_role(role_id)
            context = ToolContext(
                role=role,
                model_router=container.agent_service.model_router,
            )
            result = container.agent_service.tool_registry.run(
                "image.generate",
                context,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                out_prefix=f"{role.id}-generated",
            )
            if not result.ok:
                raise RuntimeError(result.error or "Image generation failed")
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"Image generation failed: {error}") from error

        return {
            "role_id": role.id,
            "image_url": result.data["image_url"],
            "image_path": result.data["image_path"],
            "prompt": result.data["prompt"],
            "aspect_ratio": result.data["aspect_ratio"],
        }

    @app.get("/api/benchmark/summary")
    def benchmark_summary() -> dict:
        return container.benchmark_runner.summary()

    @app.post("/api/benchmark/run")
    def benchmark_run(payload: dict | None = None) -> dict:
        payload = payload or {}
        try:
            return container.benchmark_runner.run(
                role_ids=payload.get("role_ids"),
                model_ids=payload.get("model_ids"),
                case_ids=payload.get("case_ids"),
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"Benchmark run failed: {error}") from error

    @app.get("/api/benchmark/runs/{run_id}")
    def benchmark_run_detail(run_id: str) -> dict:
        try:
            return container.benchmark_runner.get_run(run_id)
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    return app


app = create_app()
