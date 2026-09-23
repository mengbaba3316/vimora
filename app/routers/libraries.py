import mimetypes
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AssetGroup, AssetImage
from ..schemas import GroupIn
from ..services import storage

router = APIRouter(prefix="/libraries", tags=["libraries"])
LIBS = ("face", "outfit", "socks", "pose")


def _lib(library: str) -> str:
    if library not in LIBS: raise HTTPException(404, "素材库不存在")
    return library


def _group_of(library: str, gid: int, db: Session) -> AssetGroup:
    """取组并校验归属：不存在或不属于该 library 一律 404（防跨库越权）。"""
    g = db.get(AssetGroup, gid)
    if g is None or g.library != library: _raise(404, "组不存在")
    return g


def _image_of(library: str, img_id: int, db: Session) -> AssetImage:
    """取图片并校验归属：不存在或不属于该 library 一律 404。"""
    i = db.get(AssetImage, img_id)
    if i is None or i.library != library: _raise(404, "图片不存在")
    return i


@router.get("/{library}/groups")
def list_groups(library: str, db: Session = Depends(get_db)):
    _lib(library)
    gs = db.query(AssetGroup).filter_by(library=library).order_by(AssetGroup.sort_order, AssetGroup.id).all()
    return [{"id": g.id, "name": g.name, "sort_order": g.sort_order,
             "image_count": len(g.images)} for g in gs]


@router.post("/{library}/groups")
def create_group(library: str, body: GroupIn, db: Session = Depends(get_db)):
    _lib(library)
    if db.query(AssetGroup).filter_by(library=library, name=body.name).first():
        raise HTTPException(400, "同库下已存在同名组")
    g = AssetGroup(library=library, name=body.name); db.add(g); db.commit(); db.refresh(g)
    return {"id": g.id, "name": g.name, "sort_order": g.sort_order, "image_count": 0}


@router.put("/{library}/groups/{gid}")
def update_group(library: str, gid: int, body: GroupIn, db: Session = Depends(get_db)):
    _lib(library)
    g = _group_of(library, gid, db)
    if body.name != g.name and \
            db.query(AssetGroup).filter_by(library=library, name=body.name).first():
        raise HTTPException(400, "同库下已存在同名组")
    g.name = body.name; db.commit(); return {"id": g.id, "name": g.name}


@router.delete("/{library}/groups/{gid}")
def delete_group(library: str, gid: int, db: Session = Depends(get_db)):
    _lib(library)
    g = _group_of(library, gid, db)
    for img in list(g.images): storage.delete_image(img.file_path)
    db.delete(g); db.commit(); return {"ok": True}


@router.get("/{library}/images")
def list_images(library: str, group_id: Optional[int] = None, keyword: str = "",
                db: Session = Depends(get_db)):
    _lib(library)
    q = db.query(AssetImage).filter_by(library=library)
    if group_id: q = q.filter_by(group_id=group_id)
    if keyword: q = q.filter(AssetImage.original_name.like(f"%{keyword}%"))
    return [{"id": i.id, "group_id": i.group_id, "group_name": i.group.name,
             "library": i.library, "original_name": i.original_name,
             "file_path": i.file_path, "sort_order": i.sort_order,
             "url": f"/files/libraries/{i.file_path}",
             "created_at": str(i.created_at)} for i in q.order_by(AssetImage.id).all()]


@router.post("/{library}/images")
async def upload_images(library: str, group_id: int = Form(...), files: List[UploadFile] = File(...),
                        db: Session = Depends(get_db)):
    _lib(library)
    g = _group_of(library, group_id, db)  # 组不存在或跨库均 404，防 library 列与组不一致
    imported, errors = 0, []
    for f in files:
        data = await f.read()
        if f.content_type not in storage.ALLOWED: errors.append(f"{f.filename}: 类型不支持"); continue
        if len(data) > storage.MAX_SIZE: errors.append(f"{f.filename}: 超过 20MB"); continue
        rel = storage.save_image(library, g.id, f.filename, data)
        db.add(AssetImage(library=library, group_id=g.id,
                          original_name=f.filename, file_path=rel))
        imported += 1
    db.commit()
    if errors and imported == 0: raise HTTPException(400, "；".join(errors))
    return {"imported": imported, "skipped": len(errors), "errors": errors}


@router.put("/{library}/images/{img_id}")
def update_image(library: str, img_id: int, body: dict, db: Session = Depends(get_db)):
    _lib(library)
    i = _image_of(library, img_id, db)
    if "group_id" in body:
        # 目标组必须存在于本库，否则 404（防止悬挂 group_id / 跨库越权）
        _group_of(library, int(body["group_id"]), db)
    for k in ("original_name", "group_id", "sort_order"):
        if k in body: setattr(i, k, body[k])
    db.commit(); return {"ok": True}


@router.delete("/{library}/images/{img_id}")
def delete_image(library: str, img_id: int, db: Session = Depends(get_db)):
    _lib(library)
    i = _image_of(library, img_id, db)
    storage.delete_image(i.file_path)
    db.delete(i); db.commit(); return {"ok": True}


class ImportDirIn(BaseModel):
    source_dir: str


@router.post("/{library}/import-dir")
def import_dir(library: str, body: ImportDirIn, db: Session = Depends(get_db)):
    """磁盘批量导入：一级子目录→组（递归读全部文件），根散图→「未分组」组。

    组计数口径与测试对齐：目录/「未分组」已存在同名组 = 并入（groups_merged），
    新建 = groups_created；不存在的 source_dir → 400。
    """
    _lib(library)
    src = body.source_dir
    if not os.path.isdir(src): raise HTTPException(400, "后端机器上不存在该目录")
    stats = {"groups_created": 0, "groups_merged": 0, "images_imported": 0, "skipped": 0}

    def ensure_group(name: str):
        g = db.query(AssetGroup).filter_by(library=library, name=name).first()
        if g is not None: return g, False
        g = AssetGroup(library=library, name=name); db.add(g); db.flush()
        return g, True

    def import_file(path: str, group: AssetGroup):
        fn = os.path.basename(path)
        with open(path, "rb") as fh: data = fh.read()
        mime = mimetypes.guess_type(fn)[0]
        if mime not in storage.ALLOWED or len(data) > storage.MAX_SIZE:
            stats["skipped"] += 1; return
        rel = storage.save_image(library, group.id, fn, data)
        db.add(AssetImage(library=library, group_id=group.id,
                          original_name=fn, file_path=rel))
        stats["images_imported"] += 1

    def walk_dir(d: str, group: AssetGroup):
        for root, _, files in os.walk(d):
            for fn in files:
                import_file(os.path.join(root, fn), group)

    loose, created = ensure_group("未分组")
    stats["groups_created" if created else "groups_merged"] += 1
    for name in os.listdir(src):
        p = os.path.join(src, name)
        if os.path.isdir(p):
            g, created = ensure_group(name)
            stats["groups_created" if created else "groups_merged"] += 1
            walk_dir(p, g)
        else:
            import_file(p, loose)
    db.commit()
    return stats


def _raise(code, msg): raise HTTPException(code, msg)
