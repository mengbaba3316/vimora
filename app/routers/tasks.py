from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AssetImage, GenTask, Provider
from ..services import task_runner

router = APIRouter(prefix="/tasks", tags=["tasks"])


class AssetIn(BaseModel):
    library: str
    image_ids: List[int]


class TaskIn(BaseModel):
    prompt_id: Optional[int] = None
    prompt_name: str = Field(min_length=1, max_length=100)
    prompt_content: str = Field(min_length=1)
    provider_id: int
    model: Optional[str] = None
    size: Optional[str] = None
    quality: Optional[str] = None
    n: Optional[int] = Field(default=None, ge=1, le=10)
    extra: Optional[dict] = None
    # 前端工作台对无值字段发显式 JSON null（assets:null/extra:null/prompt_id:null），须容忍
    assets: Optional[List[AssetIn]] = None


def _fmt(dt) -> Optional[str]:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def _file_path_map(db: Session, tasks: List[GenTask]) -> dict:
    """快照引用的全部素材 id → 当前 file_path（一次查询，供详情真实缩略图）。"""
    ids = sorted({i for t in tasks for a in (t.assets or [])
                  for i in (a.get("image_ids") or [])})
    if not ids:
        return {}
    rows = (db.query(AssetImage.id, AssetImage.file_path)
              .filter(AssetImage.id.in_(ids)).all())
    return {r.id: r.file_path for r in rows}


def to_dict(t: GenTask, file_paths: Optional[dict] = None) -> dict:
    assets = t.assets
    if assets and file_paths is not None:
        # 快照补 file_paths（与 image_ids 按位对齐；素材已删的位为 null），
        # 历史详情据此渲染 /files/libraries 真实缩略图
        assets = [{**a, "file_paths": [file_paths.get(i)
                                       for i in (a.get("image_ids") or [])]}
                  for a in assets]
    return {
        "id": t.id, "status": t.status, "error_message": t.error_message,
        "prompt_id": t.prompt_id, "prompt_name": t.prompt_name,
        "prompt_content": t.prompt_content,
        "provider_id": t.provider_id, "provider_name": t.provider_name,
        "endpoint": t.endpoint, "model": t.model, "size": t.size,
        "quality": t.quality, "n": t.n, "extra": t.extra, "assets": assets,
        "output_dir": t.output_dir, "remote_task_id": t.remote_task_id,
        "images": [{"id": im.id, "file_path": im.file_path,
                    "url": f"/files/outputs/{im.file_path}"} for im in t.images],
        "created_at": _fmt(t.created_at), "started_at": _fmt(t.started_at),
        "finished_at": _fmt(t.finished_at),
    }


@router.get("")
def list_tasks(status: str = "", keyword: str = "", prompt_id: Optional[int] = None,
               page: int = 1, size: int = 50, db: Session = Depends(get_db)):
    page = max(1, page)
    size = min(max(1, size), 200)
    q = db.query(GenTask)
    if status:
        q = q.filter(GenTask.status == status)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(or_(GenTask.prompt_name.like(like),
                         GenTask.prompt_content.like(like)))
    if prompt_id:
        q = q.filter(GenTask.prompt_id == prompt_id)
    total = q.count()
    items = (q.order_by(GenTask.id.desc())
             .offset((page - 1) * size).limit(size).all())
    paths = _file_path_map(db, items)
    return {"items": [to_dict(t, paths) for t in items], "total": total,
            "page": page, "size": size}


@router.post("", status_code=202)
def create_task(body: TaskIn, db: Session = Depends(get_db)):
    p = db.get(Provider, body.provider_id)
    if not p:
        raise HTTPException(400, "源站不存在")
    n_max = ((p.param_options or {}).get("n_max"))
    if body.n and n_max and body.n > n_max:
        raise HTTPException(400, f"张数 n={body.n} 超过该源站上限 {n_max}")
    # 每张图必须真实存在于对应 library（id 与 library 联合校验），否则 400 指明缺失
    assets = body.assets or []                # 显式 null → 走既定默认（空列表 → generations）
    flat_ids = [i for a in assets for i in a.image_ids]
    found = {}
    if flat_ids:
        for r in db.query(AssetImage).filter(AssetImage.id.in_(flat_ids)).all():
            found[r.id] = r
    for a in assets:
        for i in a.image_ids:
            r = found.get(i)
            if r is None or r.library != a.library:
                raise HTTPException(400, f"{a.library} 库中不存在图片 id={i}")
    endpoint = "edits" if flat_ids else "generations"
    # 快照按规格 §4.1 补全 group_id/group_name（组信息取该条素材的首张图）
    snap_assets = []
    for a in assets:
        rows = [found[i] for i in a.image_ids]
        snap_assets.append({
            "library": a.library,
            "group_id": rows[0].group_id if rows else None,
            "group_name": rows[0].group.name if rows else None,
            "image_ids": a.image_ids,
        })
    t = GenTask(prompt_id=body.prompt_id, prompt_name=body.prompt_name,
                prompt_content=body.prompt_content, provider_id=p.id,
                provider_name=p.name, endpoint=endpoint,
                model=body.model or p.default_model,
                size=body.size or p.default_size,
                quality=body.quality or p.default_quality,
                n=body.n or 1, extra=body.extra,
                assets=snap_assets or None)
    db.add(t)
    db.commit()
    db.refresh(t)
    task_runner.submit(t.id)
    return {"id": t.id, "status": t.status}


@router.get("/{tid}")
def get_task(tid: int, db: Session = Depends(get_db)):
    t = _one(db, tid)
    return to_dict(t, _file_path_map(db, [t]))


@router.post("/{tid}/rerun")
def rerun_task(tid: int, db: Session = Depends(get_db)):
    """以该任务快照复制全部字段新建任务并提交执行。"""
    old = _one(db, tid)
    t = GenTask(prompt_id=old.prompt_id, prompt_name=old.prompt_name,
                prompt_content=old.prompt_content, provider_id=old.provider_id,
                provider_name=old.provider_name, endpoint=old.endpoint,
                model=old.model, size=old.size, quality=old.quality,
                n=old.n, extra=old.extra, assets=old.assets)
    db.add(t)
    db.commit()
    db.refresh(t)
    task_runner.submit(t.id)
    return {"id": t.id, "status": t.status}


@router.delete("/{tid}")
def delete_task(tid: int, db: Session = Depends(get_db)):
    """只删记录（级联 task_image），磁盘成果文件保留（防误删）。"""
    t = _one(db, tid)
    db.delete(t)
    db.commit()
    return {"ok": True}


def _one(db: Session, tid: int) -> GenTask:
    t = db.get(GenTask, tid)
    if not t:
        raise HTTPException(404, "任务不存在")
    return t
