from fastapi import FastAPI

from .database import init_app_db
from .routers import prompts


def create_app():
    app = FastAPI(title="生图工作台 API")
    init_app_db()
    app.include_router(prompts.router, prefix="/api")
    return app


app = create_app()
