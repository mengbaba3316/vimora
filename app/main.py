import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import database
from .config import settings
from .database import init_app_db
from .models import GenTask
from .routers import prompts, libraries, providers, tasks
from .services import generator, storage, task_runner


def create_app():
    # Swagger/ReDoc/OpenAPI 挂到 /api 前缀下，与 REST 路由同级
    app = FastAPI(title="生图工作台 API", docs_url="/api/docs",
                  redoc_url="/api/redoc", openapi_url="/api/openapi.json")
    init_app_db()
    # 存储/生成器的落盘根目录统一由 settings 决定（测试中可 monkeypatch）
    storage.DATA_DIR = settings.DATA_DIR
    generator.DATA_DIR = settings.DATA_DIR
    generator.OUTPUT_DIR = settings.OUTPUT_DIR
    os.makedirs(os.path.join(settings.DATA_DIR, "libraries"), exist_ok=True)
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    app.include_router(prompts.router, prefix="/api")
    app.include_router(libraries.router, prefix="/api")
    app.include_router(providers.router, prefix="/api")
    app.include_router(tasks.router, prefix="/api")
    app.mount("/files/libraries", StaticFiles(directory=os.path.join(settings.DATA_DIR, "libraries")), name="libfiles")
    app.mount("/files/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outfile")
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
