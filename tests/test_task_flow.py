import os
import time

from .test_storage_libraries_api import png_bytes


def _wait_terminal(client, tid, timeout=15):
    """轮询任务至终态（Mock sleep 2s + 落盘，15s 足够），返回最后的任务详情。"""
    deadline = time.time() + timeout
    t = {}
    while time.time() < deadline:
        t = client.get(f"/api/tasks/{tid}").json()
        if t["status"] in ("success", "failed"):
            return t
        time.sleep(0.3)
    return t


def _setup_provider_and_assets(client):
    pid = client.post("/api/providers", json={"name": "Mock", "type": "mock",
                                              "po_n_max": 10}).json()["id"]
    gid = client.post("/api/libraries/face/groups", json={"name": "模特A"}).json()["id"]
    client.post("/api/libraries/face/images", data={"group_id": str(gid)},
                files=[("files", ("a.png", png_bytes(), "image/png"))])
    img = client.get(f"/api/libraries/face/images?group_id={gid}").json()[0]
    return pid, img["id"]


def test_task_success_flow(client, settings, monkeypatch):
    from app.services import task_runner
    pid, img_id = _setup_provider_and_assets(client)
    r = client.post("/api/tasks", json={
        "prompt_name": "街拍白裙", "prompt_content": "A photo", "provider_id": pid,
        "model": "gpt-image-1", "size": "1024x1024", "quality": "high", "n": 1,
        "assets": [{"library": "face", "image_ids": [img_id]}]})
    assert r.status_code == 202
    tid = r.json()["id"]
    task = _wait_terminal(client, tid)
    assert task["status"] == "success", task.get("error_message")
    assert len(task["images"]) == 1
    assert task["assets"][0]["group_name"] == "模特A"       # 快照补全 group
    # 结果图真实落盘，url 指向 /files/outputs 静态挂载
    img0 = task["images"][0]
    assert img0["url"].startswith("/files/outputs/")
    assert os.path.exists(os.path.join(settings.OUTPUT_DIR,
                                       *img0["file_path"].split("/")))
    assert os.path.exists(os.path.join(settings.OUTPUT_DIR,
                                       *task["output_dir"].split("/"), "task.json"))
    assert client.post(f"/api/tasks/{tid}/rerun").status_code == 200


def test_task_generations_when_no_assets(client, settings):
    pid = client.post("/api/providers", json={"name": "Mock", "type": "mock"}).json()["id"]
    tid = client.post("/api/tasks", json={"prompt_name": "纯文", "prompt_content": "x",
                                          "provider_id": pid, "n": 1}).json()["id"]
    t = _wait_terminal(client, tid)
    assert t["endpoint"] == "generations" and t["status"] == "success"


def test_explicit_null_payload_creates_generations_task(client, settings):
    """前端工作台对无值字段发显式 JSON null，须容忍并走既定默认逻辑（assets:null → generations）。"""
    pid = client.post("/api/providers", json={"name": "Mock", "type": "mock"}).json()["id"]
    r = client.post("/api/tasks", json={
        "prompt_id": None, "prompt_name": "空值容忍", "prompt_content": "x",
        "provider_id": pid, "model": None, "size": None, "quality": None,
        "n": None, "extra": None, "assets": None})
    assert r.status_code == 202
    t = _wait_terminal(client, r.json()["id"])
    assert t["status"] == "success", t.get("error_message")
    assert t["endpoint"] == "generations"
    # None → 落源站默认值，assets/extra 保持 None
    assert t["model"] == "gpt-image-1" and t["assets"] is None and t["extra"] is None


def test_missing_asset_fails(client):
    pid = client.post("/api/providers", json={"name": "Mock", "type": "mock"}).json()["id"]
    r = client.post("/api/tasks", json={"prompt_name": "x", "prompt_content": "x",
                                        "provider_id": pid,
                                        "assets": [{"library": "face", "image_ids": [99999]}]})
    assert r.status_code == 400 and "不存在" in r.json()["detail"]


def test_non_200_response_marks_task_failed(client, monkeypatch):
    """规格 §8：源站非 200 响应 → 任务 failed，错误信息含状态码与响应体。"""
    pid = client.post("/api/providers", json={
        "name": "B", "type": "openai", "base_url": "https://b.com",
        "api_key": "k"}).json()["id"]

    class FakeResp:
        status_code = 500
        text = "internal error: quota exceeded"

        def json(self):
            return {}

    import app.services.task_runner as R
    monkeypatch.setattr(R.requests, "post", lambda *a, **k: FakeResp())
    tid = client.post("/api/tasks", json={"prompt_name": "失败", "prompt_content": "x",
                                          "provider_id": pid, "n": 1}).json()["id"]
    t = _wait_terminal(client, tid)
    assert t["status"] == "failed"
    assert "HTTP 500" in t["error_message"] and "quota exceeded" in t["error_message"]
    assert t["finished_at"] is not None


def test_rerun_with_deleted_asset_fails(client, settings):
    """I-1：rerun 时快照素材已被删除 → 任务 failed，错误信息含库名与缺失 id（不静默跳过）。"""
    pid = client.post("/api/providers", json={"name": "Mock", "type": "mock",
                                              "po_n_max": 10}).json()["id"]
    gid = client.post("/api/libraries/face/groups", json={"name": "模特B"}).json()["id"]
    client.post("/api/libraries/face/images", data={"group_id": str(gid)},
                files=[("files", ("a.png", png_bytes(), "image/png")),
                       ("files", ("b.png", png_bytes(), "image/png"))])
    imgs = client.get(f"/api/libraries/face/images?group_id={gid}").json()
    assert len(imgs) == 2
    r = client.post("/api/tasks", json={
        "prompt_name": "两张参考", "prompt_content": "A photo", "provider_id": pid,
        "n": 1, "assets": [{"library": "face", "image_ids": [imgs[0]["id"], imgs[1]["id"]]}]})
    tid = r.json()["id"]
    t = _wait_terminal(client, tid)
    assert t["status"] == "success", t.get("error_message")

    # 删掉其中一张素材后 rerun：快照里的 id 已查不到
    assert client.delete(f"/api/libraries/face/images/{imgs[1]['id']}").status_code == 200
    r2 = client.post(f"/api/tasks/{tid}/rerun")
    assert r2.status_code == 200
    t2 = _wait_terminal(client, r2.json()["id"])
    assert t2["status"] == "failed"
    assert "face" in t2["error_message"] and str(imgs[1]["id"]) in t2["error_message"]
    assert t2["images"] == []   # 缺图任务不产生任何产物

def test_rerun_copies_snapshot_and_delete_keeps_disk(client, settings):
    pid = client.post("/api/providers", json={"name": "Mock", "type": "mock"}).json()["id"]
    tid = client.post("/api/tasks", json={"prompt_name": "快照", "prompt_content": "y",
                                          "provider_id": pid, "n": 1}).json()["id"]
    t = _wait_terminal(client, tid)
    r = client.post(f"/api/tasks/{tid}/rerun")
    assert r.status_code == 200
    # rerun 任务同样必须轮询至终态：否则 teardown（drop_all）后 worker 线程
    # 仍在跑，monkeypatch 解除后会把 Mock 图写进真实 outputs/ 目录
    t2 = _wait_terminal(client, r.json()["id"])
    assert t2["status"] == "success", t2.get("error_message")
    assert len(t2["images"]) == t["n"]
    assert (t2["prompt_name"], t2["prompt_content"], t2["endpoint"], t2["model"],
            t2["size"], t2["quality"], t2["n"], t2["provider_id"],
            t2["provider_name"]) == (t["prompt_name"], t["prompt_content"], t["endpoint"],
                                     t["model"], t["size"], t["quality"], t["n"],
                                     t["provider_id"], t["provider_name"])
    # delete 只删记录（含 task_image），磁盘文件保留
    out_dir = os.path.join(settings.OUTPUT_DIR, *t["output_dir"].split("/"))
    assert os.path.exists(out_dir)
    assert client.delete(f"/api/tasks/{tid}").status_code == 200
    assert client.get(f"/api/tasks/{tid}").status_code == 404
    assert os.path.exists(out_dir)
