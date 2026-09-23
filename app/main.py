import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_app_db
from .routers import prompts, libraries, providers


def create_app():
    app = FastAPI(title="生图工作台 API")
    init_app_db()
    os.makedirs(os.path.join(settings.DATA_DIR, "libraries"), exist_ok=True)
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    app.include_router(prompts.router, prefix="/api")
    app.include_router(libraries.router, prefix="/api")
    app.include_router(providers.router, prefix="/api")
    app.mount("/files/libraries", StaticFiles(directory=os.path.join(settings.DATA_DIR, "libraries")), name="libfiles")
    return app


app = create_app()
