def test_crud_and_search(client):
    r = client.post("/api/prompts", json={"name": "街拍白裙", "content": "A photo", "tags": "街拍"})
    assert r.status_code == 200 and r.json()["id"] > 0
    pid = r.json()["id"]
    r = client.post("/api/prompts", json={"name": "森系", "content": "forest", "tags": "外景"})
    assert r.status_code == 200
    assert client.get("/api/prompts?keyword=白裙").json()["total"] == 1
    assert client.get("/api/prompts").json()["total"] == 2
    r = client.put(f"/api/prompts/{pid}", json={"name": "街拍白裙V2", "content": "A photo2", "tags": ""})
    assert r.json()["name"] == "街拍白裙V2"
    assert client.delete(f"/api/prompts/{pid}").status_code == 200
    assert client.get(f"/api/prompts/{pid}").status_code == 404
    assert client.post("/api/prompts", json={"name": "", "content": "x"}).status_code == 422


def test_prompt_out_fields_and_tag_filter(client):
    r = client.post("/api/prompts", json={"name": "A", "content": "x", "tags": "街拍,白裙"})
    assert r.status_code == 200
    body = r.json()
    # 规格 §5.1：响应含 created_at/updated_at，格式 yyyy-MM-dd HH:mm:ss
    for k in ("created_at", "updated_at"):
        assert len(body[k]) == 19 and body[k][4] == "-" and body[k][10] == " ", body[k]
    client.post("/api/prompts", json={"name": "B", "content": "y", "tags": "森系"})
    # tag 精确匹配（按逗号拆分后包含）：单 tag
    assert client.get("/api/prompts?tag=街拍").json()["total"] == 1
    # 多 tag AND：A 同时含 街拍+白裙
    assert client.get("/api/prompts?tag=街拍,白裙").json()["total"] == 1
    assert client.get("/api/prompts?tag=森系").json()["total"] == 1
    # 精确匹配不误伤子串：tag「白」≠「白裙」
    assert client.get("/api/prompts?tag=白").json()["total"] == 0
    assert client.get("/api/prompts?tag=不存在").json()["total"] == 0
    # 带 tag 后分页 total 反映过滤结果
    d = client.get("/api/prompts?tag=街拍").json()
    assert d["total"] == 1 and len(d["items"]) == 1
