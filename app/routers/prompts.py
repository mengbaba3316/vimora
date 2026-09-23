from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Prompt
from ..schemas import PromptIn, PromptOut

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("")
def list_prompts(keyword: str = "", tag: str = "", page: int = Query(1, ge=1),
                 size: int = Query(50, le=200), db: Session = Depends(get_db)):
    q = db.query(Prompt)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(Prompt.name.like(like) | Prompt.content.like(like) | Prompt.tags.like(like))
    if tag:
        # 规格 §5.1：tag 精确匹配——查询 tag 按逗号拆分后须全部包含在提示词 tags 里
        wanted = {t.strip() for t in tag.split(",") if t.strip()}
        ps = [p for p in q.order_by(Prompt.id.desc()).all()
              if wanted <= {t.strip() for t in p.tags.split(",") if t.strip()}]
        total = len(ps)
        items = ps[(page - 1) * size:(page - 1) * size + size]
    else:
        total = q.count()
        items = q.order_by(Prompt.id.desc()).offset((page - 1) * size).limit(size).all()
    return {"items": [PromptOut.model_validate(i) for i in items],
            "total": total, "page": page, "size": size}


@router.post("")
def create_prompt(body: PromptIn, db: Session = Depends(get_db)):
    p = Prompt(**body.model_dump()); db.add(p); db.commit(); db.refresh(p)
    return PromptOut.model_validate(p)


@router.get("/{pid}")
def get_prompt(pid: int, db: Session = Depends(get_db)):
    p = db.get(Prompt, pid) or _404()
    return PromptOut.model_validate(p)


@router.put("/{pid}")
def update_prompt(pid: int, body: PromptIn, db: Session = Depends(get_db)):
    p = db.get(Prompt, pid) or _404()
    for k, v in body.model_dump().items(): setattr(p, k, v)
    db.commit()
    return PromptOut.model_validate(p)


@router.delete("/{pid}")
def delete_prompt(pid: int, db: Session = Depends(get_db)):
    p = db.get(Prompt, pid) or _404()
    db.delete(p); db.commit(); return {"ok": True}


def _404(): raise HTTPException(404, "提示词不存在")
