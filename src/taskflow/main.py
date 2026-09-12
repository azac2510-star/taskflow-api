from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from taskflow.api.routes import auth, projects, tasks
from taskflow.config import get_settings
from taskflow.database import init_db

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(initialize_database: bool = True) -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if initialize_database and settings.auto_create_tables:
            init_db()
        yield

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Multi-user project and task management REST API.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"])
    def health_check() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    @app.get("/demo", include_in_schema=False)
    def demo_console() -> FileResponse:
        return FileResponse(STATIC_DIR / "demo.html")

    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(projects.router, prefix="/api/v1")
    app.include_router(tasks.project_tasks_router, prefix="/api/v1")
    app.include_router(tasks.task_router, prefix="/api/v1")
    return app


app = create_app()
