import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
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
    # 托管前端 SPA（frontend 任务 8 遗留）：dist 存在才挂载，且必须在所有 /api 路由与
    # /files 挂载之后注册——Mount("/") 会兜住其余全部路径，先注册会遮蔽 API 与文件服务。
    # dist 缺失（未执行 npm run build）时跳过，纯后端模式不受影响。
    dist = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "frontend", "dist")
    if os.path.isdir(dist):
        index_html = os.path.join(dist, "index.html")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str):
            """Vue Router history 模式深链接兜底：无对应静态文件的路径返回 SPA 入口。"""
            # 未知 /api、/files 请求不做 SPA 兜底，维持 404
            if full_path == "api" or full_path.startswith("api/") \
                    or full_path == "files" or full_path.startswith("files/"):
                raise HTTPException(status_code=404)
            # dist 内真实存在的静态资源（/assets/*、/favicon.svg）按原文件伺服
            candidate = os.path.realpath(os.path.join(dist, full_path))
            if candidate.startswith(os.path.realpath(dist) + os.sep) \
                    and os.path.isfile(candidate):
                return FileResponse(candidate)
            # 深链接（/history 等）刷新 → 返回 SPA 入口，由前端路由接管
            return FileResponse(index_html)

        # 注意顺序：Starlette 按注册顺序取第一个完全匹配的路由，Mount("/") 会吞掉所有
        # GET——兜底路由若注册在它之后则永远不可达（深链接刷新仍会 404），故必须在前。
        app.mount("/", StaticFiles(directory=dist, html=True), name="spa")
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
