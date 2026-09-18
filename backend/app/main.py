import time
from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.checkpoint.memory import InMemorySaver
from starlette.middleware.base import BaseHTTPMiddleware

from app.agents.graph import build_purchase_graph
from app.agents.runtime import WorkflowRuntime
from app.agents.services import (
    DatabaseApprovalAuthority,
    DatabaseTransactionExecutor,
    WorkflowServices,
)
from app.api.v1.router import api_router
from app.api.v1.websocket import RealtimeHub
from app.api.v1.whatsapp import router as whatsapp_router
from app.channels.voice.pipeline import VoicePipeline
from app.channels.voice.protocol import VoiceIntentType
from app.channels.voice.sarvam import SarvamVoiceProvider
from app.core.config import Settings, get_settings
from app.core.errors import VyapaarError
from app.core.logging import configure_logging
from app.domain.enums import ApprovalStatus
from app.infrastructure.db.checkpoint import postgres_checkpointer
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.observability.metrics import api_latency
from app.infrastructure.observability.sentry import configure_sentry
from app.infrastructure.observability.tracing import configure_tracing
from app.infrastructure.redis.client import RedisManager
from app.integrations.suppliers.mock_supplier import MockSupplierAdapter
from app.ml.demand.baseline import BaselineForecaster

logger = structlog.get_logger()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        duration_ms = (time.perf_counter() - started) * 1000
        api_latency.record(duration_ms, {"method": request.method, "route": request.url.path})
        logger.info(
            "request_complete",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        return response


def _wire_runtime(app: FastAPI, settings: Settings, checkpointer) -> None:
    supplier = MockSupplierAdapter(
        signing_secret=settings.a2a_signing_secret.get_secret_value(),
        buyer_agent_id=settings.a2a_agent_id,
    )
    app.state.mock_supplier = supplier
    authority = DatabaseApprovalAuthority(
        get_session_factory(),
        secret=settings.auth_approval_secret.get_secret_value(),
        algorithm=settings.auth_jwt_algorithm,
        ttl_minutes=settings.auth_approval_token_minutes,
    )
    executor = DatabaseTransactionExecutor(get_session_factory(), authority, [supplier])
    services = WorkflowServices(
        forecast_model=BaselineForecaster(),
        suppliers=[supplier],
        approval_authority=authority,
        transaction_executor=executor,
    )
    app.state.workflow_runtime = WorkflowRuntime(
        build_purchase_graph(services, checkpointer=checkpointer), authority
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = app.state.settings
    app.state.redis = RedisManager(settings.redis_url)
    app.state.realtime_hub = RealtimeHub()
    app.state.voice_sessions = {}
    app.state.voice_pipeline = None
    if settings.sarvam_api_key:
        provider = SarvamVoiceProvider(
            api_key=settings.sarvam_api_key.get_secret_value(),
            stt_model=settings.sarvam_stt_model,
            tts_model=settings.sarvam_tts_model,
            tts_speaker=settings.sarvam_tts_speaker,
        )

        async def handle_voice(session, intent) -> str:
            if intent.intent in {
                VoiceIntentType.APPROVE_ACTIVE_PROPOSAL,
                VoiceIntentType.MODIFY_ACTIVE_PROPOSAL,
                VoiceIntentType.REJECT_ACTIVE_PROPOSAL,
            }:
                if (
                    not session.active_request_id
                    or not session.active_proposal_id
                    or not session.approval_token
                ):
                    return (
                        "No authenticated active purchase proposal is linked to this voice session."
                    )
                action = {
                    VoiceIntentType.APPROVE_ACTIVE_PROPOSAL: ApprovalStatus.APPROVED,
                    VoiceIntentType.MODIFY_ACTIVE_PROPOSAL: ApprovalStatus.MODIFIED,
                    VoiceIntentType.REJECT_ACTIVE_PROPOSAL: ApprovalStatus.REJECTED,
                }[intent.intent]
                await app.state.workflow_runtime.resume(
                    merchant_id=session.merchant_id,
                    request_id=session.active_request_id,
                    action=action,
                    approval_token=session.approval_token,
                    quantity=float(intent.quantity) if intent.quantity else None,
                    user_id=session.user_id,
                    expected_proposal_id=session.active_proposal_id,
                )
                return f"Purchase proposal {action.value.lower()}."
            if intent.intent == VoiceIntentType.REQUEST_PURCHASE:
                return "I understood the purchase request. Review the generated proposal before approval."
            if intent.intent == VoiceIntentType.REPORT_LOW_STOCK:
                return "Low inventory noted. I will check the demand forecast before proposing a purchase."
            return "I could not map that request to a safe business action."

        app.state.voice_pipeline = VoicePipeline(provider, handle_voice)

    if settings.app_checkpointer == "postgres":
        async with postgres_checkpointer(settings.database_url) as checkpointer:
            _wire_runtime(app, settings, checkpointer)
            yield
    else:
        _wire_runtime(app, settings, InMemorySaver())
        yield
    await app.state.redis.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    selected = settings or get_settings()
    configure_logging(selected.app_log_level)
    configure_sentry(
        selected.sentry_dsn.get_secret_value() if selected.sentry_dsn else None,
        environment=selected.app_env,
    )
    app = FastAPI(
        title="Vyapaar Commander API",
        version="0.1.0",
        docs_url="/docs" if selected.app_env != "production" else None,
        lifespan=lifespan,
    )
    app.state.settings = selected
    app.add_middleware(
        CORSMiddleware,
        allow_origins=selected.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)
    app.include_router(api_router)
    app.include_router(whatsapp_router)

    @app.exception_handler(VyapaarError)
    async def handle_domain_error(request: Request, exc: VyapaarError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": getattr(request.state, "request_id", None),
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_FAILED",
                    "message": "Request validation failed",
                    "request_id": getattr(request.state, "request_id", None),
                    "details": {"errors": jsonable_encoder(exc.errors())},
                }
            },
        )

    configure_tracing(
        app,
        enabled=selected.telemetry_enabled,
        otlp_endpoint=selected.telemetry_otlp_endpoint,
    )
    return app


app = create_app()
