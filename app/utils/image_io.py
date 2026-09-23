import base64

import requests


def save_b64(b64: str, path: str):
    with open(path, "wb") as f:
        f.write(base64.b64decode(b64))


def download(url: str, path: str, tries: int = 2) -> str:
    """下载到 path，成功返回响应的 Content-Type（可能为空串），重试耗尽抛异常。"""
    for i in range(tries):
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 200:
                with open(path, "wb") as f:
                    f.write(r.content)
                return r.headers.get("Content-Type", "")
        except Exception:
            if i == tries - 1:
                raise
    raise RuntimeError(f"下载失败 {url}")
