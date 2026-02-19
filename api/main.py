from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.deps import get_settings
from api.routes.projects import router as projects_router
from api.routes.files import router as files_router
from api.routes.run_configs import router as run_configs_router
from api.routes.runs import router as runs_router


logger = logging.getLogger("vrs_api")


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
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_logging(request: Request, call_next):  # type: ignore[no-untyped-def]
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        logger.info(
            "request method=%s path=%s status=%s elapsed_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "db": "unknown", "storage": "unknown"}

    app.include_router(projects_router, prefix="/v1")
    app.include_router(files_router, prefix="/v1")
    app.include_router(run_configs_router, prefix="/v1")
    app.include_router(runs_router, prefix="/v1")

    return app


app = create_app()
