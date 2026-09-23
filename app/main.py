import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import database
from .config import settings
from .database import init_app_db
from .models import GenTask
from .routers import prompts, libraries, providers
from .services import task_runner


def create_app():
    app = FastAPI(title="生图工作台 API")
    init_app_db()
    os.makedirs(os.path.join(settings.DATA_DIR, "libraries"), exist_ok=True)
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    app.include_router(prompts.router, prefix="/api")
    app.include_router(libraries.router, prefix="/api")
    app.include_router(providers.router, prefix="/api")
    app.mount("/files/libraries", StaticFiles(directory=os.path.join(settings.DATA_DIR, "libraries")), name="libfiles")
    # 后台生图执行器（init_app_db 之后 database.SessionLocal 才有值，须取模块属性）
    task_runner.init_runner(database.SessionLocal, settings.MAX_CONCURRENT_TASKS)
    # 服务重启：遗留 pending/running 一律置为 failed
    s = database.SessionLocal()
    s.query(GenTask).filter(GenTask.status.in_(("pending", "running"))).update(
        {"status": "failed", "error_message": "服务重启，任务中断"},
        synchronize_session=False)
    s.commit()
    s.close()
    return app


app = create_app()
