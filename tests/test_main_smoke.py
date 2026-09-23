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
