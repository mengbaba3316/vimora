"""素材库（一级库）管理接口测试。"""


def test_library_type_crud(client):
    # 种子库存在（迁移在 ensure_database 时灌入）
    libs = client.get("/api/library-types").json()
    assert [l["key"] for l in libs] == ["face", "outfit", "pose"]
    assert all(l["enabled"] for l in libs)

    # 英文名建库 → key 用名称 slug
    r = client.post("/api/library-types", json={"name": "shoes"})
    assert r.status_code == 200, r.text
    assert r.json()["key"] == "shoes"
    lid = r.json()["id"]

    # 中文名建库 → key 退化为 lib_{id}
    r2 = client.post("/api/library-types", json={"name": "鞋包"})
    assert r2.status_code == 200
    assert r2.json()["key"] == f"lib_{r2.json()['id']}"

    # 同名建库 → 400
    assert client.post("/api/library-types", json={"name": "shoes"}).status_code == 400
    # 与种子库同名 → 400
    assert client.post("/api/library-types", json={"name": "人脸"}).status_code == 400

    # 改名 / 停用 / 排序
    assert client.put(f"/api/library-types/{lid}",
                      json={"name": "Shoes", "enabled": False, "sort_order": 9}).status_code == 200
    body = client.get("/api/library-types").json()
    row = next(l for l in body if l["id"] == lid)
    assert row["name"] == "Shoes" and row["enabled"] is False and row["sort_order"] == 9

    # 库下有组时禁止删库
    gid = client.post("/api/libraries/1/groups", json={"name": "临时组"}).json()["id"]
    assert client.delete("/api/library-types/1").status_code == 400
    # 空库可删（含组先建后删清空）
    assert client.delete(f"/api/libraries/1/groups/{gid}").status_code == 200
    assert client.delete("/api/library-types/1").status_code == 200
    assert all(l["id"] != 1 for l in client.get("/api/library-types").json())
