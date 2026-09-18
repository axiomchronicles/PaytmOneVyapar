import asyncio
import time
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
import structlog
from fastapi import FastAPI, HTTPException, Request
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
from app.application.services.activity_service import (
    DatabaseA2ARecorder,
    DatabaseWorkflowActivityRecorder,
)
from app.application.services.auth_service import (
    EmailOtpDelivery,
    MultiChannelOtpDelivery,
    OAuthTokenVerifier,
    WhatsAppOtpDelivery,
)
from app.channels.voice.i18n import get_voice_message
from app.channels.voice.pipeline import VoicePipeline
from app.channels.voice.protocol import VoiceIntentType
from app.channels.voice.sarvam import SarvamVoiceProvider
from app.core.config import Settings, get_settings
from app.core.errors import VyapaarError
from app.core.logging import configure_logging
from app.domain.enums import ApprovalStatus
from app.infrastructure.db.checkpoint import postgres_checkpointer
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.events.realtime import RedisRealtimeBridge
from app.infrastructure.observability.metrics import api_latency
from app.infrastructure.observability.sentry import configure_sentry
from app.infrastructure.observability.tracing import configure_tracing
from app.infrastructure.redis.client import RedisManager
from app.integrations.email.resend import ResendEmailProvider
from app.integrations.suppliers.mock_supplier import MockSupplierAdapter
from app.integrations.whatsapp.meta import MetaWhatsAppProvider
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
        message_recorder=DatabaseA2ARecorder(get_session_factory()),
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
        activity_recorder=DatabaseWorkflowActivityRecorder(get_session_factory()),
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
    app.state.oauth_verifier = OAuthTokenVerifier()
    app.state.provider_http_client = httpx.AsyncClient(timeout=30)
    app.state.email_provider = None

    whatsapp_delivery = None
    if all(
        [
            settings.whatsapp_access_token,
            settings.whatsapp_phone_number_id,
            settings.whatsapp_graph_api_version,
        ]
    ):
        whatsapp = MetaWhatsAppProvider(
            access_token=settings.whatsapp_access_token.get_secret_value(),
            phone_number_id=settings.whatsapp_phone_number_id,
            graph_api_version=settings.whatsapp_graph_api_version,
            client=app.state.provider_http_client,
        )
        whatsapp_delivery = WhatsAppOtpDelivery(whatsapp.send_text)

    email_delivery = None
    if settings.resend_api_key:
        email_provider = ResendEmailProvider(
            api_key=settings.resend_api_key.get_secret_value(),
            from_email=settings.resend_from_email,
            client=app.state.provider_http_client,
        )
        app.state.email_provider = email_provider
        email_delivery = EmailOtpDelivery(email_provider.send_otp)

    if whatsapp_delivery or email_delivery:
        app.state.otp_delivery = MultiChannelOtpDelivery(
            whatsapp=whatsapp_delivery,
            email=email_delivery,
        )
    else:
        app.state.otp_delivery = None

    logger.info(
        "otp_configuration",
        whatsapp_delivery_enabled=whatsapp_delivery is not None,
        email_delivery_enabled=email_delivery is not None,
        delivery_enabled=app.state.otp_delivery is not None,
    )
    logger.info(
        "resend_configuration",
        provider="resend",
        api_key_present=settings.resend_api_key is not None,
        from_email=settings.resend_from_email,
        enabled=email_delivery is not None,
    )
    logger.info(
        "oauth_configuration",
        google_client_id_present=bool(settings.google_oauth_client_id),
        google_client_secret_present=bool(settings.google_oauth_client_secret),
        apple_client_id_present=bool(settings.apple_oauth_client_id),
    )
    if settings.sarvam_api_key:
        logger.info(
            "sarvam_configuration",
            provider="sarvam",
            credential_present=True,
            credential_length=len(settings.sarvam_api_key.get_secret_value()),
            credential_source="SARVAM_API_KEY",
            stt_enabled=True,
            tts_enabled=True,
        )
        provider = SarvamVoiceProvider(
            api_key=settings.sarvam_api_key.get_secret_value(),
            stt_model=settings.sarvam_stt_model,
            tts_model=settings.sarvam_tts_model,
            tts_speaker=settings.sarvam_tts_speaker,
            tts_pace=settings.sarvam_tts_pace,
            tts_temperature=settings.sarvam_tts_temperature,
            tts_sample_rate=settings.sarvam_tts_sample_rate,
            tts_codec=settings.sarvam_tts_codec,
            tts_bitrate=settings.sarvam_tts_bitrate,
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
                    return get_voice_message("no_active_proposal", session.language_code)
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
                if action == ApprovalStatus.APPROVED:
                    return get_voice_message("proposal_approved", session.language_code)
                elif action == ApprovalStatus.MODIFIED:
                    return get_voice_message("proposal_modified", session.language_code)
                return get_voice_message("proposal_rejected", session.language_code)
            if intent.intent == VoiceIntentType.REQUEST_PURCHASE:
                return get_voice_message("purchase_request", session.language_code)
            if intent.intent == VoiceIntentType.REPORT_LOW_STOCK:
                return get_voice_message("low_stock", session.language_code)
            return get_voice_message("unknown_action", session.language_code)

        app.state.voice_pipeline = VoicePipeline(provider, handle_voice)
    else:
        logger.warning(
            "sarvam_configuration",
            provider="sarvam",
            credential_present=False,
            credential_length=0,
            credential_source="SARVAM_API_KEY",
            stt_enabled=False,
            tts_enabled=False,
        )

    bridge = RedisRealtimeBridge(app.state.redis.client, app.state.realtime_hub)
    bridge_task = asyncio.create_task(bridge.run(), name="redis-realtime-bridge")
    try:
        if settings.app_checkpointer == "postgres":
            async with postgres_checkpointer(settings.database_url) as checkpointer:
                _wire_runtime(app, settings, checkpointer)
                yield
        else:
            _wire_runtime(app, settings, InMemorySaver())
            yield
    finally:
        bridge.stop()
        bridge_task.cancel()
        await asyncio.gather(bridge_task, return_exceptions=True)
        await app.state.provider_http_client.aclose()
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
                    "details": {
                        "errors": [
                            {
                                "loc": list(error.get("loc", ())),
                                "msg": error.get("msg", "Invalid value"),
                                "type": error.get("type", "validation_error"),
                            }
                            for error in exc.errors()
                        ]
                    },
                }
            },
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
        messages = {
            401: "Authentication is required.",
            403: "You do not have permission for this action.",
            404: "The requested resource was not found.",
        }
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": messages.get(exc.status_code, str(exc.detail)),
                    "request_id": getattr(request.state, "request_id", None),
                    "details": {},
                }
            },
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_request_error", error_type=type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "The request could not be completed.",
                    "request_id": getattr(request.state, "request_id", None),
                    "details": {},
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
