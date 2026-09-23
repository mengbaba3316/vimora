import io
import os

from PIL import Image


def png_bytes():
    b = io.BytesIO(); Image.new("RGB", (8, 8), (200, 60, 60)).save(b, "PNG")
    return b.getvalue()

def test_group_crud(client):
    r = client.post("/api/libraries/face/groups", json={"name": "模特A"})
    assert r.status_code == 200 and r.json()["image_count"] == 0
    assert client.post("/api/libraries/face/groups", json={"name": "模特A"}).status_code == 400
    gid = client.get("/api/libraries/face/groups").json()[0]["id"]
    assert client.put(f"/api/libraries/face/groups/{gid}", json={"name": "模特B"}).status_code == 200
    assert client.delete(f"/api/libraries/face/groups/{gid}").status_code == 200

def test_upload_list_delete_image(client, settings):
    gid = client.post("/api/libraries/socks/groups", json={"name": "白袜"}).json()["id"]
    r = client.post(f"/api/libraries/socks/images",
                    data={"group_id": str(gid)},
                    files=[("files", ("细节1.png", png_bytes(), "image/png")),
                           ("files", ("细节2.png", png_bytes(), "image/png"))])
    assert r.status_code == 200 and r.json()["imported"] == 2
    imgs = client.get(f"/api/libraries/socks/images?group_id={gid}").json()
    assert len(imgs) == 2 and imgs[0]["url"].startswith("/files/libraries/socks/")
    # file_path 相对 DATA_DIR/libraries（与静态挂载 /files/libraries 一致），简报测试行漏了 libraries 段
    path = os.path.join(settings.DATA_DIR, "libraries", imgs[0]["file_path"])
    assert os.path.exists(path)
    bad = client.post(f"/api/libraries/socks/images", data={"group_id": str(gid)},
                      files=[("files", ("x.gif", b"GIF89a", "image/gif"))])
    assert bad.status_code == 400
    img_id = imgs[0]["id"]
    assert client.delete(f"/api/libraries/socks/images/{img_id}").status_code == 200
    assert not os.path.exists(path)
