import json
import os
from typing import List, Optional, Tuple

from ..utils import image_io
from ..utils.filenames import stamp

OUTPUT_DIR = "outputs"   # main 启动时由 settings 覆盖；测试可 monkeypatch
DATA_DIR = "data"        # 素材读取根目录；main 启动时由 settings 覆盖；测试可 monkeypatch


def build_request(p, t, image_files: Optional[List[Tuple]] = None):
    """拼一次生图请求，返回 (method, url, kwargs)。

    image_files 为 [(字段名, (文件名, bytes, mime)), ...] 的展开列表，
    字段名统一改写为 p.image_field；p.extra_params（源站固定附加字段）最后合并。
    """
    image_files = image_files or []
    # 瞬态（未 flush）的 Provider 上列默认值是 None，这里兜底为与模型列默认一致
    gen_path = p.gen_path or "/v1/images/generations"
    edits_path = p.edits_path or "/v1/images/edits"
    image_field = p.image_field or "image[]"
    params = {"prompt": t.prompt_content, "model": t.model, "n": t.n, "size": t.size}
    if t.quality:
        params["quality"] = t.quality
    if t.extra:
        params.update(t.extra)

    if t.endpoint == "edits":
        method, url = "POST", p.base_url + edits_path
        data = {k: v if isinstance(v, str) else str(v) for k, v in params.items()}
        if p.extra_params:
            data.update(p.extra_params)
        kwargs = {"data": data, "files": [(image_field, f[1]) for f in image_files]}
    else:
        method, url = "POST", p.base_url + gen_path
        if p.extra_params:
            params.update(p.extra_params)
        kwargs = {"json": params}

    kwargs["headers"] = {"Authorization": f"Bearer {p.api_key}"}
    kwargs["timeout"] = p.timeout_seconds
    return method, url, kwargs


def save_results(t, resp_json: dict, out_dir: str) -> List[str]:
    """把响应 data 里的图片落盘（b64 直接解码 / url 下载），返回实际写入的路径。

    url 分支按 Content-Type 修正扩展名（jpeg→.jpg、webp→.webp，默认 .png）。
    """
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    ts = stamp()
    for i, item in enumerate(resp_json.get("data", []), start=1):
        fp = os.path.join(out_dir, f"{ts}_{i}.png")
        final = fp
        if item.get("b64_json"):
            image_io.save_b64(item["b64_json"], fp)
        elif item.get("url"):
            ct = image_io.download(item["url"], fp)
            if "jpeg" in ct:
                final = fp[:-4] + ".jpg"
            elif "webp" in ct:
                final = fp[:-4] + ".webp"
            if final != fp:
                os.rename(fp, final)
        else:
            continue
        paths.append(final)
    return paths


def write_task_json(out_dir: str, task_dict: dict, files: List[str], elapsed: float):
    meta = {**task_dict, "files": [os.path.basename(f) for f in files],
            "elapsed_seconds": elapsed}
    with open(os.path.join(out_dir, "task.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
