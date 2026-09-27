import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AssetGroup, Library

router = APIRouter(prefix="/library-types", tags=["library-types"])

# 新建库未指定颜色时的默认调色板（与主题色系协调）
_PALETTE = ["#C2435B", "#0E7FA8", "#D9642A", "#A93D80", "#2E7D32", "#6D4C9F", "#B8860B"]


class LibraryIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: Optional[str] = None
    sort_order: Optional[int] = None
    enabled: Optional[bool] = None


class LibraryUpdateIn(BaseModel):
    """部分更新：None 的字段不动（区分「显式停用」与「不传」）。"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    color: Optional[str] = None
    sort_order: Optional[int] = None
    enabled: Optional[bool] = None


def to_dict(lb: Library, group_count: int = 0) -> dict:
    return {"id": lb.id, "key": lb.key, "name": lb.name, "color": lb.color,
            "sort_order": lb.sort_order, "enabled": bool(lb.enabled),
            "group_count": group_count,
            "created_at": lb.created_at.strftime("%Y-%m-%d %H:%M:%S") if lb.created_at else None}


def _group_count(db: Session, library_id: int) -> int:
    return db.query(AssetGroup).filter_by(library=library_id).count()


@router.get("")
def list_libraries(db: Session = Depends(get_db)):
    return [to_dict(lb, _group_count(db, lb.id))
            for lb in db.query(Library).order_by(Library.sort_order, Library.id).all()]


@router.post("")
def create_library(body: LibraryIn, db: Session = Depends(get_db)):
    if db.query(Library).filter_by(name=body.name).first():
        raise HTTPException(400, "已存在同名素材库")
    # key 列非空且需 id 参与（lib_{id}）：先插占位 key，flush 拿到 id 后再定稿
    lb = Library(key=f"__tmp_{uuid.uuid4().hex[:8]}",
                 name=body.name,
                 color=body.color or _PALETTE[db.query(Library).count() % len(_PALETTE)],
                 sort_order=body.sort_order if body.sort_order is not None
                 else (db.query(Library).count() + 1),
                 enabled=True if body.enabled is None else body.enabled)
    db.add(lb); db.flush()
    slug = re.sub(r"[^a-z0-9_-]", "", body.name.lower())[:50]
    if not slug or db.query(Library).filter(Library.key == slug, Library.id != lb.id).first():
        slug = f"{slug}_{lb.id}" if slug else f"lib_{lb.id}"
    lb.key = slug
    db.commit(); db.refresh(lb)
    return to_dict(lb)


@router.put("/{tid}")
def update_library(tid: int, body: LibraryUpdateIn, db: Session = Depends(get_db)):
    lb = _one(db, tid)
    if body.name is not None and body.name != lb.name:
        if db.query(Library).filter(Library.name == body.name, Library.id != tid).first():
            raise HTTPException(400, "已存在同名素材库")
        lb.name = body.name
    for k in ("color", "sort_order", "enabled"):
        if getattr(body, k) is not None:
            setattr(lb, k, getattr(body, k))
    db.commit(); db.refresh(lb)
    return to_dict(lb, _group_count(db, tid))


@router.delete("/{tid}")
def delete_library(tid: int, db: Session = Depends(get_db)):
    """仅允许删除空库（无组）；有组先清空，防误删成批素材。"""
    lb = _one(db, tid)
    if _group_count(db, tid):
        raise HTTPException(400, "该库下仍有素材组，请先删除全部组再删库")
    db.delete(lb); db.commit(); return {"ok": True}


def _one(db: Session, tid: int) -> Library:
    lb = db.get(Library, tid)
    if not lb:
        raise HTTPException(404, "素材库不存在")
    return lb
