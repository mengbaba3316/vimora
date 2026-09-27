import concurrent.futures
import os
import threading
import time
import traceback
from datetime import datetime
from typing import Optional

import requests

from . import generator
from ..models import AssetGroup, AssetImage, GenTask, Provider, TaskImage
from ..utils.filenames import stamp

executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
SessionLocal = None
# 每源站并发信号量（键=provider_id），同一站同时最多 per_provider_limit 个任务在跑；
# 全局线程池容量 = 每站上限 × 站数余量，真正的限流由信号量执行
_provider_sems: dict = {}
_per_provider_limit = 2
_sems_lock = threading.Lock()

_MIMES = {".png": "image/png", ".jpg": "image/jpeg",
          ".jpeg": "image/jpeg", ".webp": "image/webp"}


def init_runner(session_factory, max_workers: int):
    """max_workers 语义：单个源站的并发上限（.env MAX_CONCURRENT_TASKS，默认 2）。
    全局线程池给足余量（上限×8），各站互不挤占；真实限流靠每站信号量。"""
    global executor, SessionLocal, _per_provider_limit, _provider_sems
    SessionLocal = session_factory
    _per_provider_limit = max(1, max_workers)
    _provider_sems = {}
    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=_per_provider_limit * 8)


def _provider_sem(provider_id: int) -> threading.BoundedSemaphore:
    with _sems_lock:
        sem = _provider_sems.get(provider_id)
        if sem is None:
            sem = threading.BoundedSemaphore(_per_provider_limit)
            _provider_sems[provider_id] = sem
        return sem


def submit(task_id: int):
    executor.submit(_run, task_id)


def shutdown(wait: bool = True):
    """关闭执行器并（默认）等待在途任务真正结束。

    测试 fixture teardown 用：wait=False 会留下仍在运行的 worker，待测试的
    monkeypatch 解除、表 drop 之后继续执行，把产物写进真实 outputs/ 目录。
    """
    global executor
    if executor is not None:
        executor.shutdown(wait=wait)
        executor = None


def _run(task_id: int):
    db = SessionLocal()
    t = None
    sem = None
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
        sem = _provider_sem(p.id)   # 同一站并发到上限时，任务在此等待站内空位
        sem.acquire()
        files = []
        if t.endpoint == "edits":
            for grp in (t.assets or []):
                ids = grp["image_ids"]
                rows = (db.query(AssetImage).join(AssetGroup)
                        .filter(AssetImage.id.in_(ids),
                                AssetImage.library == grp["library"])
                        .order_by(AssetImage.id).all())
                # 规格 §4.1：快照素材在执行时必须齐全。缺图（被删除/跨库）不再静默
                # 跳过，直接置 failed 并指明缺失 id，避免用户拿到缺参考图的产物。
                if len(rows) != len(set(ids)):
                    found = {r.id for r in rows}
                    missing = [i for i in ids if i not in found]
                    raise RuntimeError(f"{grp['library']}/{grp.get('group_name')} "
                                       f"缺失图片 id={missing}")
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
        elif p.mode == "async":
            from . import async_adapter
            # 提交成功即落库 remote_task_id：即使后续轮询失败/超时，
            # 用户也能凭此 id 到中转站后台追回（可能已扣费出图）
            t.remote_task_id = async_adapter.submit(p, url, kwargs)
            db.commit()
            resp, _ = async_adapter.poll_until_terminal(p, t.remote_task_id)
        else:
            try:
                resp = requests.post(url, **kwargs)
            except requests.exceptions.Timeout:
                raise RuntimeError(
                    f"请求超时：{p.timeout_seconds} 秒内未收到响应。中转站可能已扣费出图，"
                    f"可到其后台确认取图；若该站经常超时，请在「API 源站」编辑里调大「超时（秒）」。")
            if resp.status_code != 200:
                # 规格 §8：非 200 响应不抛请求层异常，任务置 failed 并留全量诊断信息
                raise RuntimeError(f"HTTP {resp.status_code}\n{resp.text[:2000]}")
            resp = resp.json()
        # 按天归档：outputs/YYYY-MM-DD/，所有源站的成果图共用，不按提示词/任务分层
        out_dir = os.path.join(generator.OUTPUT_DIR, stamp("%Y-%m-%d"))
        paths, missing = generator.save_results(t, resp, out_dir=out_dir)
        if not paths:
            detail = "；".join(m.get("reason", "") for m in missing if m.get("reason"))
            raise RuntimeError("中转站未返回任何图片"
                               + (f"（{detail}）" if detail else ""))
        for fp in paths:
            rel = os.path.relpath(fp, generator.OUTPUT_DIR).replace("\\", "/")
            db.add(TaskImage(task_id=t.id, file_path=rel))
        t.output_dir = os.path.relpath(out_dir, generator.OUTPUT_DIR).replace("\\", "/")
        t.status = "success"
        t.finished_at = datetime.now()   # 置终态之后写 task_{id}.json，快照即最终状态
        generator.write_task_json(out_dir, _snapshot(t), paths,
                                  time.time() - started, missing=missing)
    except Exception as e:
        if t is not None:
            t.status = "failed"
            t.error_message = (str(e) or traceback.format_exc())[:2000]
    finally:
        if sem is not None:
            sem.release()
        if t is not None:
            if t.finished_at is None:
                t.finished_at = datetime.now()
            try:
                db.commit()
            except Exception:
                # running 状态落库失败时先回滚：既避免 PendingRollbackError
                # 在 finally 里炸出第二个异常吞掉原始异常，也释放连接事务
                db.rollback()
                traceback.print_exc()
        db.close()   # 挪到外层：任务记录不存在（t is None）的早退路径也要释放连接


def _snapshot(t: GenTask) -> dict:
    """任务全字段快照，供输出目录的 task_{id}.json（人类可读、可脱离平台检索）。"""
    return {
        "id": t.id, "prompt_id": t.prompt_id, "prompt_name": t.prompt_name,
        "prompt_content": t.prompt_content, "provider_id": t.provider_id,
        "provider_name": t.provider_name, "endpoint": t.endpoint, "model": t.model,
        "size": t.size, "quality": t.quality, "n": t.n, "extra": t.extra,
        "assets": t.assets, "status": t.status,
        "output_dir": t.output_dir, "remote_task_id": t.remote_task_id,
        "created_at": t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else None,
        "started_at": t.started_at.strftime("%Y-%m-%d %H:%M:%S") if t.started_at else None,
        "finished_at": t.finished_at.strftime("%Y-%m-%d %H:%M:%S") if t.finished_at else None,
        "error_message": t.error_message,
    }


def _mime(file_path: str) -> str:
    return _MIMES.get(os.path.splitext(file_path)[1].lower(), "image/png")
