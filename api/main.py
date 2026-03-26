from __future__ import annotations

import logging
import re
import time
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.deps import get_settings
from api.deps import get_supabase_client
from api.routes.cut_contour_rules import router as cut_contour_rules_router
from api.routes.cut_rule_sets import router as cut_rule_sets_router
from api.routes.projects import router as projects_router
from api.routes.files import router as files_router
from api.routes.parts import router as parts_router
from api.routes.postprocessor_profiles import router as postprocessor_profiles_router
from api.routes.project_manufacturing_selection import router as project_manufacturing_selection_router
from api.routes.project_strategy_scoring_selection import scoring_router as project_scoring_selection_router
from api.routes.project_strategy_scoring_selection import strategy_router as project_run_strategy_selection_router
from api.routes.project_part_requirements import router as project_part_requirements_router
from api.routes.run_batches import router as run_batches_router
from api.routes.project_sheet_inputs import router as project_sheet_inputs_router
from api.routes.sheets import router as sheets_router
from api.routes.run_configs import router as run_configs_router
from api.routes.run_strategy_profiles import router as run_strategy_profiles_router
from api.routes.runs import router as runs_router
from api.routes.scoring_profiles import router as scoring_profiles_router
from api.supabase_client import SupabaseClient


logger = logging.getLogger("vrs_api")
_API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def _sanitize_request_id(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    candidate = raw_value.strip()
    if not candidate:
        return None
    if _REQUEST_ID_PATTERN.fullmatch(candidate) is None:
        return None
    return candidate


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="VRS Nesting Web API",
        version="0.3.1-phase3-fixes",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        if settings.enable_security_headers:
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
            response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
            response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
            response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
            if request.url.path.startswith("/v1/") or request.url.path == "/health":
                response.headers.setdefault("Content-Security-Policy", _API_CSP)
        return response

    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        start = time.perf_counter()
        request_id = _sanitize_request_id(request.headers.get("x-request-id")) or str(uuid4())
        correlation_id = _sanitize_request_id(request.headers.get("x-correlation-id")) or request_id
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        response.headers.setdefault("X-Request-Id", request_id)
        response.headers.setdefault("X-Correlation-Id", correlation_id)
        logger.info(
            "event=request method=%s path=%s status=%s elapsed_ms=%.2f request_id=%s correlation_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
            correlation_id,
        )
        return response

    @app.get("/health")
    def health(supabase: SupabaseClient = Depends(get_supabase_client)) -> dict[str, str]:
        db_ok = supabase.ping_rest()
        storage_ok = supabase.ping_storage()
        status_text = "ok" if db_ok and storage_ok else "degraded"
        return {
            "status": status_text,
            "db": "ok" if db_ok else "error",
            "storage": "ok" if storage_ok else "error",
        }

    app.include_router(cut_contour_rules_router, prefix="/v1")
    app.include_router(cut_rule_sets_router, prefix="/v1")
    app.include_router(projects_router, prefix="/v1")
    app.include_router(files_router, prefix="/v1")
    app.include_router(parts_router, prefix="/v1")
    app.include_router(postprocessor_profiles_router, prefix="/v1")
    app.include_router(project_manufacturing_selection_router, prefix="/v1")
    app.include_router(project_run_strategy_selection_router, prefix="/v1")
    app.include_router(project_scoring_selection_router, prefix="/v1")
    app.include_router(project_part_requirements_router, prefix="/v1")
    app.include_router(run_batches_router, prefix="/v1")
    app.include_router(project_sheet_inputs_router, prefix="/v1")
    app.include_router(sheets_router, prefix="/v1")
    app.include_router(run_configs_router, prefix="/v1")
    app.include_router(run_strategy_profiles_router, prefix="/v1")
    app.include_router(runs_router, prefix="/v1")
    app.include_router(scoring_profiles_router, prefix="/v1")

    return app


app = create_app()
