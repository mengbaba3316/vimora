import os

import pytest


def test_full_app_boots_and_serves():
    from app.main import app
    # 简报测试用 httpx.Client + ASGITransport，但 httpx>=0.28 的 ASGITransport 仅支持
    # 异步 Client（conftest 既有事实），断言不变，改用 FastAPI 官方 TestClient。
    from fastapi.testclient import TestClient
    c = TestClient(app)
    assert c.get("/api/prompts").status_code == 200
    assert c.get("/api/libraries/face/groups").status_code == 200
    assert c.get("/api/providers").status_code == 200
    assert c.get("/api/tasks").status_code == 200
    assert c.get("/api/docs").status_code == 200      # Swagger 可用


def test_static_files_mounted():
    from app.main import app
    routes = {getattr(r, "path", "") for r in app.routes}
    assert "/files/libraries" in routes and "/files/outputs" in routes
    assert "/api/tasks" in routes and "/api/prompts" in routes
    assert "/api/libraries/{library}/groups" in routes
    assert "/api/providers/{pid}" in routes


_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "frontend", "dist")


@pytest.mark.skipif(not os.path.isdir(_DIST), reason="frontend/dist 未构建")
def test_spa_deeplink_refresh_serves_index_html():
    """Vue Router history 模式：深链接刷新不得 404，须回退 SPA 入口 index.html。"""
    from fastapi.testclient import TestClient

    from app.main import app
    c = TestClient(app)
    r = c.get("/history")
    assert r.status_code == 200
    assert '<div id="app">' in r.text
    assert c.get("/").status_code == 200                      # 根路径仍可访问
    # 静态资源按原文件伺服，不被兜底覆盖成 HTML
    fav = c.get("/favicon.svg")
    assert fav.status_code == 200 and "image/svg" in fav.headers["content-type"]
    # 未知 API 路径不被 SPA 兜底吞掉
    assert c.get("/api/nonexistent-path").status_code == 404
