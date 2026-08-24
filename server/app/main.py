import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import uvicorn

from server.app.config import settings
from server.app.routes import exec, files, system

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("pi-push-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info(" Raspberry Pi File Push & Remote Exec API Started")
    logger.info(f" Host: {settings.host}:{settings.port}")
    logger.info(f" Base Directory: {settings.base_dir}")
    logger.info(f" Command Exec Enabled: {settings.enable_exec}")
    logger.info(f" Swagger Docs: http://{settings.host}:{settings.port}/docs")
    logger.info("=" * 60)
    yield
    logger.info("Shutting down Raspberry Pi File Push API...")


app = FastAPI(
    title="Raspberry Pi File Push & Exec API",
    description="Direct REST API to upload files, write content, browse directories, and execute shell commands on your Raspberry Pi.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for all origins (useful when interacting via web apps or local dev tools)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to Swagger documentation."""
    return RedirectResponse(url="/docs")


# Include routers under root and under /api/v1 for convenience
app.include_router(system.router)
app.include_router(files.router)
app.include_router(exec.router)

# Versioned prefixes
app.include_router(system.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")
app.include_router(exec.router, prefix="/api/v1")


def start():
    """Entrypoint function to run uvicorn."""
    uvicorn.run(
        "server.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False
    )


if __name__ == "__main__":
    start()
