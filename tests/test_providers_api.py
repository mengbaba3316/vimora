def test_provider_crud(client, monkeypatch):
    body = {"name": "中转站A", "type": "openai", "base_url": "https://api.a.com",
            "api_key": "sk-test", "param_options": {"size": ["1:1"], "n_max": 4}}
    pid = client.post("/api/providers", json=body).json()["id"]
    lst = client.get("/api/providers").json()
    assert lst[0]["name"] == "中转站A" and lst[0]["param_options"]["n_max"] == 4
    client.put(f"/api/providers/{pid}", json={**body, "enabled": False})
    assert client.get(f"/api/providers/{pid}").json()["enabled"] is False

def test_connectivity(client, monkeypatch):
    pid = client.post("/api/providers", json={
        "name": "A", "type": "openai", "base_url": "https://api.a.com", "api_key": "k"}).json()["id"]
    class FakeResp:
        status_code = 200
        def json(self): return {"data": [{"id": "m"}] * 42}
    calls = {}
    def fake_get(url, headers=None, timeout=None):
        calls["url"] = url; calls["auth"] = headers.get("Authorization")
        return FakeResp()
    import app.routers.providers as P
    # providers.py 按简报用 `import requests as http`（模块级引用）；该语句只绑定 http 名，
    # P.requests 不存在，故 patch 同一模块对象的 P.http（等价于 patch requests.get）
    monkeypatch.setattr(P.http, "get", fake_get)
    r = client.post(f"/api/providers/{pid}/test").json()
    assert r["ok"] is True and r["model_count"] == 42
    assert calls["url"] == "https://api.a.com/v1/models" and calls["auth"] == "Bearer k"

def test_update_blank_api_key_keeps_old(client):
    pid = client.post("/api/providers", json={
        "name": "A", "type": "openai", "base_url": "https://a.com",
        "api_key": "sk-keep"}).json()["id"]
    # 模拟前端启停开关：全字段 PUT 但省略 api_key → 不应清空已存 Key，其他字段正常更新
    body = {"name": "A2", "type": "openai", "base_url": "https://a2.com", "enabled": False}
    r = client.put(f"/api/providers/{pid}", json=body)
    assert r.status_code == 200
    after = client.get(f"/api/providers/{pid}").json()
    assert after["api_key"] == "sk-keep" and after["enabled"] is False and after["name"] == "A2"
    # 显式传空串/纯空白同样保留原 Key
    client.put(f"/api/providers/{pid}", json={**body, "api_key": "   "})
    assert client.get(f"/api/providers/{pid}").json()["api_key"] == "sk-keep"

def test_update_new_api_key_overrides(client):
    pid = client.post("/api/providers", json={
        "name": "B", "type": "openai", "base_url": "https://b.com", "api_key": "old"}).json()["id"]
    client.put(f"/api/providers/{pid}", json={
        "name": "B", "type": "openai", "base_url": "https://b.com", "api_key": "new-key"})
    assert client.get(f"/api/providers/{pid}").json()["api_key"] == "new-key"

def test_mock_connectivity(client):
    mid = client.post("/api/providers", json={"name": "Mock", "type": "mock"}).json()["id"]
    assert client.post(f"/api/providers/{mid}/test").json()["ok"] is True

def test_bad_key_result(client, monkeypatch):
    pid = client.post("/api/providers", json={
        "name": "B", "type": "openai", "base_url": "https://b.com", "api_key": "bad"}).json()["id"]
    class FakeResp:
        status_code = 401
        def json(self): return {}
    import app.routers.providers as P
    monkeypatch.setattr(P.http, "get", lambda *a, **k: FakeResp())
    r = client.post(f"/api/providers/{pid}/test").json()
    assert r["ok"] is False and "401" in r["message"]
