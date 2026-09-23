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
