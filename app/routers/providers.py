from typing import Optional

import requests as http
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Provider
from ..schemas import ProviderIn

router = APIRouter(prefix="/providers", tags=["providers"])


def to_dict(p: Provider) -> dict:
    """只输出真实列（排除 _sa_instance_state），供列表/详情/增改统一返回。"""
    return {
        "id": p.id, "name": p.name, "type": p.type, "base_url": p.base_url,
        "api_key": p.api_key, "enabled": p.enabled, "gen_path": p.gen_path,
        "edits_path": p.edits_path, "image_field": p.image_field,
        "default_model": p.default_model, "default_size": p.default_size,
        "default_quality": p.default_quality, "timeout_seconds": p.timeout_seconds,
        "mode": p.mode, "task_query_path": p.task_query_path,
        "poll_interval_seconds": p.poll_interval_seconds,
        "extra_params": p.extra_params, "param_options": p.param_options,
        "available_models": p.available_models,
        "remark": p.remark,
        "created_at": p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else None,
        "updated_at": p.updated_at.strftime("%Y-%m-%d %H:%M:%S") if p.updated_at else None,
    }


@router.get("")
def list_providers(db: Session = Depends(get_db)):
    return [to_dict(p) for p in db.query(Provider).order_by(Provider.id).all()]


@router.post("")
def create(body: ProviderIn, db: Session = Depends(get_db)):
    p = Provider(**body.model_dump()); db.add(p); db.commit(); db.refresh(p)
    return to_dict(p)


@router.get("/{pid}")
def get_one(pid: int, db: Session = Depends(get_db)):
    return to_dict(_one(db, pid))


@router.put("/{pid}")
def update(pid: int, body: ProviderIn, db: Session = Depends(get_db)):
    p = _one(db, pid)
    old_key = p.api_key
    for k, v in body.model_dump().items(): setattr(p, k, v)
    # 空串/省略/纯空白的 api_key → 保留原 Key（前端启停 PUT 不携带 Key，不能被默认值清掉）
    if not (body.api_key or "").strip(): p.api_key = old_key
    db.commit(); db.refresh(p)
    return to_dict(p)


@router.delete("/{pid}")
def delete(pid: int, db: Session = Depends(get_db)):
    p = _one(db, pid); db.delete(p); db.commit(); return {"ok": True}


@router.post("/{pid}/test")
def test_conn(pid: int, db: Session = Depends(get_db)):
    """连通性测试：GET {base_url}/v1/models，超时 5s。mock 类型不发起网络请求。
    成功时把拉到的全量模型 id 缓存进 available_models，供工作台模型下拉使用。"""
    p = _one(db, pid)
    if p.type == "mock":
        return {"ok": True, "status_code": 0, "model_count": 0, "models": [],
                "message": "Mock 源站，本地联调"}
    try:
        r = http.get(f"{p.base_url}/v1/models",
                     headers={"Authorization": f"Bearer {p.api_key}"}, timeout=5)
    except Exception as e:
        return {"ok": False, "status_code": 0, "model_count": 0, "models": [],
                "message": str(e)[:200]}
    if r.status_code != 200:
        return {"ok": False, "status_code": r.status_code, "model_count": 0,
                "models": [], "message": f"HTTP {r.status_code}"}
    data = (r.json() or {}).get("data", [])
    ids = [str(m.get("id")) for m in data if m.get("id")][:300]
    # 缓存进源站记录：更新时间随之刷新，工作台重新选择源站即拿到新列表
    p.available_models = ids
    db.commit()
    return {"ok": True, "status_code": 200, "model_count": len(ids),
            "models": ids, "message": "连通正常"}


def _one(db: Session, pid: int) -> Optional[Provider]:
    p = db.get(Provider, pid)
    if not p: raise HTTPException(404, "源站不存在")
    return p
