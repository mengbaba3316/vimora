import io
import os

from PIL import Image


def png_bytes():
    b = io.BytesIO(); Image.new("RGB", (8, 8), (200, 60, 60)).save(b, "PNG")
    return b.getvalue()

def test_group_crud(client):
    r = client.post("/api/libraries/1/groups", json={"name": "模特A"})
    assert r.status_code == 200 and r.json()["image_count"] == 0
    assert client.post("/api/libraries/1/groups", json={"name": "模特A"}).status_code == 400
    gid = client.get("/api/libraries/1/groups").json()[0]["id"]
    assert client.put(f"/api/libraries/1/groups/{gid}", json={"name": "模特B"}).status_code == 200
    assert client.delete(f"/api/libraries/1/groups/{gid}").status_code == 200

def test_upload_list_delete_image(client, settings):
    gid = client.post("/api/libraries/3/groups", json={"name": "站姿"}).json()["id"]
    r = client.post(f"/api/libraries/3/images",
                    data={"group_id": str(gid)},
                    files=[("files", ("细节1.png", png_bytes(), "image/png")),
                           ("files", ("细节2.png", png_bytes(), "image/png"))])
    assert r.status_code == 200 and r.json()["imported"] == 2
    imgs = client.get(f"/api/libraries/3/images?group_id={gid}").json()
    assert len(imgs) == 2 and imgs[0]["url"].startswith("/files/libraries/pose/")
    # file_path 相对 DATA_DIR/libraries（与静态挂载 /files/libraries 一致），简报测试行漏了 libraries 段
    path = os.path.join(settings.DATA_DIR, "libraries", imgs[0]["file_path"])
    assert os.path.exists(path)
    bad = client.post(f"/api/libraries/3/images", data={"group_id": str(gid)},
                      files=[("files", ("x.gif", b"GIF89a", "image/gif"))])
    assert bad.status_code == 400
    img_id = imgs[0]["id"]
    assert client.delete(f"/api/libraries/3/images/{img_id}").status_code == 200
    assert not os.path.exists(path)


def test_update_image_move_group_guard(client):
    g1 = client.post("/api/libraries/1/groups", json={"name": "A"}).json()["id"]
    g2 = client.post("/api/libraries/1/groups", json={"name": "B"}).json()["id"]
    gx = client.post("/api/libraries/3/groups", json={"name": "别库组"}).json()["id"]
    client.post("/api/libraries/1/images", data={"group_id": str(g1)},
                files=[("files", ("a.png", png_bytes(), "image/png"))])
    img_id = client.get("/api/libraries/1/images").json()[0]["id"]
    # 移到不存在的组 → 404（而非写出悬挂 group_id）
    assert client.put(f"/api/libraries/1/images/{img_id}",
                      json={"group_id": 99999}).status_code == 404
    # 移到跨库的组 → 404
    assert client.put(f"/api/libraries/1/images/{img_id}",
                      json={"group_id": gx}).status_code == 404
    # 本库正常移动 → 200 且移动生效
    assert client.put(f"/api/libraries/1/images/{img_id}",
                      json={"group_id": g2}).status_code == 200
    assert client.get(f"/api/libraries/1/images?group_id={g2}").json()[0]["id"] == img_id


def test_group_rename_dup_and_cross_library_guards(client):
    g1 = client.post("/api/libraries/1/groups", json={"name": "A"}).json()["id"]
    g2 = client.post("/api/libraries/1/groups", json={"name": "B"}).json()["id"]
    # 改名撞同库已有名 → 400（而非唯一约束 500）
    assert client.put(f"/api/libraries/1/groups/{g2}", json={"name": "A"}).status_code == 400
    # 改名维持自己原名（未变名）→ 200
    assert client.put(f"/api/libraries/1/groups/{g1}", json={"name": "A"}).status_code == 200
    # 不存在的 library id → 404（规格 §5.2；非数字路径参数由框架 422 拦截）
    assert client.put(f"/api/libraries/9999/groups/{g1}", json={"name": "C"}).status_code == 404
    # 跨库：face 的组走 pose 前缀 → 404
    assert client.put(f"/api/libraries/3/groups/{g1}", json={"name": "C"}).status_code == 404
    assert client.delete(f"/api/libraries/3/groups/{g1}").status_code == 404
    # 图片跨库：face 的图走 pose 前缀 → 404
    r = client.post("/api/libraries/1/images", data={"group_id": str(g1)},
                    files=[("files", ("a.png", png_bytes(), "image/png"))])
    assert r.status_code == 200
    img_id = client.get("/api/libraries/1/images").json()[0]["id"]
    assert client.put(f"/api/libraries/3/images/{img_id}",
                      json={"original_name": "z.png"}).status_code == 404
    assert client.delete(f"/api/libraries/3/images/{img_id}").status_code == 404
    # 跨库上传：pose 前缀 + face 组 → 404（防 library 列与组不一致）
    assert client.post("/api/libraries/3/images", data={"group_id": str(g1)},
                       files=[("files", ("b.png", png_bytes(), "image/png"))]).status_code == 404
    # 本库操作仍正常
    assert client.delete(f"/api/libraries/1/images/{img_id}").status_code == 200
    assert client.delete(f"/api/libraries/1/groups/{g1}").status_code == 200
