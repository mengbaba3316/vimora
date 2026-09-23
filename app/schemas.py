from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_serializer


class PromptIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=20000)
    tags: str = ""
    remark: str = ""


class PromptOut(PromptIn):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @field_serializer("created_at", "updated_at")
    def _fmt_time(self, v: Optional[datetime]) -> Optional[str]:
        # 规格 §5：时间格式 yyyy-MM-dd HH:mm:ss
        return v.strftime("%Y-%m-%d %H:%M:%S") if v else None


class GroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
