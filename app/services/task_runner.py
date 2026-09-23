import concurrent.futures
import os
import time
import traceback
from datetime import datetime
from typing import Optional

import requests

from . import generator
from ..models import AssetGroup, AssetImage, GenTask, Provider, TaskImage
from ..utils.filenames import safe_dirname, stamp

executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
SessionLocal = None

_MIMES = {".png": "image/png", ".jpg": "image/jpeg",
          ".jpeg": "image/jpeg", ".webp": "image/webp"}


def init_runner(session_factory, max_workers: int):
    global executor, SessionLocal
    SessionLocal = session_factory
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)


def submit(task_id: int):
    executor.submit(_run, task_id)


def _run(task_id: int):
    db = SessionLocal()
    t = None
    try:
        t = db.get(GenTask, task_id)
        if t is None:
            return
        t.status = "running"
        t.started_at = datetime.now()
        db.commit()
        p = db.get(Provider, t.provider_id)
        if p is None:
            raise RuntimeError("源站不存在或已删除")
        files = []
        if t.endpoint == "edits":
            for grp in (t.assets or []):
                ids = grp["image_ids"]
                rows = (db.query(AssetImage).join(AssetGroup)
                        .filter(AssetImage.id.in_(ids),
                                AssetImage.library == grp["library"])
                        .order_by(AssetImage.id).all())
                rows.sort(key=lambda r: ids.index(r.id))   # 按 image_ids 顺序展开
                for r in rows:
                    path = os.path.join(generator.DATA_DIR, "libraries", r.file_path)
                    with open(path, "rb") as f:
                        files.append((p.image_field,
                                      (r.original_name, f.read(), _mime(r.file_path))))
        _, url, kwargs = generator.build_request(p, t, image_files=files)
        started = time.time()
        if p.type == "mock":
            from . import mock_provider
            resp = mock_provider.generate(prompt=t.prompt_content, model=t.model,
                                          size=t.size, n=t.n, quality=t.quality,
                                          extra=t.extra)
        else:
            resp = requests.post(url, **kwargs).json()
        out_dir = os.path.join(generator.OUTPUT_DIR, safe_dirname(t.prompt_name),
                               f"{stamp()}_{t.id}")
        paths = generator.save_results(t, resp, out_dir=out_dir)
        if not paths:
            raise RuntimeError("中转站未返回任何图片")
        for fp in paths:
            rel = os.path.relpath(fp, generator.OUTPUT_DIR).replace("\\", "/")
            db.add(TaskImage(task_id=t.id, file_path=rel))
        t.output_dir = os.path.relpath(out_dir, generator.OUTPUT_DIR).replace("\\", "/")
        t.status = "success"
        generator.write_task_json(out_dir, _snapshot(t), paths, time.time() - started)
    except Exception as e:
        if t is not None:
            t.status = "failed"
            t.error_message = (str(e) or traceback.format_exc())[:2000]
    finally:
        if t is not None:
            t.finished_at = datetime.now()
            db.commit()
        db.close()


def _snapshot(t: GenTask) -> dict:
    """任务全字段快照，供输出目录的 task.json（人类可读、可脱离平台检索）。"""
    return {
        "id": t.id, "prompt_id": t.prompt_id, "prompt_name": t.prompt_name,
        "prompt_content": t.prompt_content, "provider_id": t.provider_id,
        "provider_name": t.provider_name, "endpoint": t.endpoint, "model": t.model,
        "size": t.size, "quality": t.quality, "n": t.n, "extra": t.extra,
        "assets": t.assets, "status": t.status,
        "output_dir": t.output_dir,
        "created_at": t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else None,
        "started_at": t.started_at.strftime("%Y-%m-%d %H:%M:%S") if t.started_at else None,
    }


def _mime(file_path: str) -> str:
    return _MIMES.get(os.path.splitext(file_path)[1].lower(), "image/png")
