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
    paths = G.save_results(t, {"data": [{"b64_json": b64}]}, out_dir=str(tmp_path / "o"))
    assert len(paths) == 1 and paths[0].endswith(".png")

def test_save_url_response(tmp_path, monkeypatch):
    from app.utils import image_io
    p, t = _task()
    monkeypatch.setattr(G, "OUTPUT_DIR", str(tmp_path))
    class R:
        status_code = 200; content = b"jpgdata"; headers = {"Content-Type": "image/jpeg"}
    monkeypatch.setattr(image_io.requests, "get", lambda *a, **k: R())
    paths = G.save_results(t, {"data": [{"url": "https://x/1.jpg"}]}, out_dir=str(tmp_path / "o"))
    assert paths[0].endswith(".jpg")

def test_mock_provider(tmp_path):
    from app.services import mock_provider
    resp = mock_provider.generate(prompt="一只白袜特写", model="m", size="1024x1024",
                                  n=1, quality="high", extra=None)
    assert resp["data"] and base64.b64decode(resp["data"][0]["b64_json"])[:4] != b""
