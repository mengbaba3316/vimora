import base64, json
from app.services import generator as G

def _task(provider_type="openai", **kw):
    from app.models import Provider, GenTask
    p = Provider(name="P", type=provider_type, base_url="https://x.com",
                 api_key="sk", default_model="m", default_size="1024x1024",
                 default_quality="high", timeout_seconds=5, **kw.get("provider_kw", {}))
    t = GenTask(prompt_id=None, prompt_name="测试", prompt_content="hi",
                provider_id=1, provider_name="P", endpoint="generations",
                model="m", size="1024x1024", quality="high", n=1, extra=None)
    return p, t

def test_build_generations_request():
    p, t = _task()
    method, url, kwargs = G.build_request(p, t, image_files=[])
    assert url.endswith("/v1/images/generations")
    assert kwargs["json"] == {"prompt": "hi", "model": "m", "n": 1, "size": "1024x1024", "quality": "high"}
    assert kwargs["headers"]["Authorization"] == "Bearer sk"

def test_build_edits_multipart():
    p, t = _task()
    t.endpoint = "edits"
    files = [("image[]", ("a.png", b"x", "image/png")), ("image[]", ("b.png", b"y", "image/png"))]
    method, url, kwargs = G.build_request(p, t, image_files=files)
    assert url.endswith("/v1/images/edits")
    assert kwargs["data"]["prompt"] == "hi" and len(kwargs["files"]) == 2
    p.image_field = "image"                       # 字段名可覆盖
    assert G.build_request(p, t, image_files=files)[2]["files"][0][0] == "image"

def test_extra_merge_and_resolution():
    p, t = _task(provider_kw={"extra_params": {"background": "transparent"}})
    t.extra = {"resolution": "4K"}
    _, _, kwargs = G.build_request(p, t, image_files=[])
    assert kwargs["json"]["background"] == "transparent" and kwargs["json"]["resolution"] == "4K"

def test_save_b64_response(tmp_path, monkeypatch):
    p, t = _task()
    monkeypatch.setattr(G, "OUTPUT_DIR", str(tmp_path))
    b64 = base64.b64encode(b"fakepng").decode()
    paths, missing = G.save_results(t, {"data": [{"b64_json": b64}]},
                                    out_dir=str(tmp_path / "o"))
    assert len(paths) == 1 and paths[0].endswith(".png") and missing == []

def test_save_url_response(tmp_path, monkeypatch):
    from app.utils import image_io
    p, t = _task()
    monkeypatch.setattr(G, "OUTPUT_DIR", str(tmp_path))
    class R:
        status_code = 200; content = b"jpgdata"; headers = {"Content-Type": "image/jpeg"}
    monkeypatch.setattr(image_io.requests, "get", lambda *a, **k: R())
    paths, missing = G.save_results(t, {"data": [{"url": "https://x/1.jpg"}]},
                                    out_dir=str(tmp_path / "o"))
    assert paths[0].endswith(".jpg") and missing == []

def test_save_results_skips_failed_single(tmp_path, monkeypatch):
    """I-2：单张下载失败不连坐——跳过并计入 missing，其余照常落盘。"""
    from app.utils import image_io
    p, t = _task()
    t.n = 2
    monkeypatch.setattr(G, "OUTPUT_DIR", str(tmp_path))
    b64 = base64.b64encode(b"fakepng").decode()

    def boom(url, path, tries=2):
        raise RuntimeError(f"下载失败 {url}")

    monkeypatch.setattr(image_io, "download", boom)
    paths, missing = G.save_results(
        t, {"data": [{"url": "https://x/bad"}, {"b64_json": b64}]},
        out_dir=str(tmp_path / "o"))
    assert len(paths) == 1 and paths[0].endswith(".png")   # b64 那张照常成功
    assert len(missing) == 1
    assert missing[0]["url"] == "https://x/bad" and missing[0]["index"] == 1
    assert "下载失败" in missing[0]["reason"]

def test_save_results_all_failed_returns_empty(tmp_path, monkeypatch):
    """I-2：全部失败返回空列表，由调用方判 failed。"""
    from app.utils import image_io
    p, t = _task()
    t.n = 2
    monkeypatch.setattr(G, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(image_io, "download",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    paths, missing = G.save_results(
        t, {"data": [{"url": "https://x/1"}, {"url": "https://x/2"}]},
        out_dir=str(tmp_path / "o"))
    assert paths == [] and len(missing) == 2

def test_mock_provider(tmp_path):
    from app.services import mock_provider
    resp = mock_provider.generate(prompt="一只白袜特写", model="m", size="1024x1024",
                                  n=1, quality="high", extra=None)
    assert resp["data"] and base64.b64decode(resp["data"][0]["b64_json"])[:4] != b""
