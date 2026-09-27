from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_serializer, model_validator


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


class ProviderIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    # 仅两种源站类型；非法值 422（而非落库时 Enum 炸 500）
    type: Literal["openai", "mock"] = "openai"
    base_url: str = ""
    api_key: str = ""
    enabled: bool = True
    gen_path: str = "/v1/images/generations"
    edits_path: str = "/v1/images/edits"
    image_field: str = "image[]"
    default_model: str = "gpt-image-1"
    default_size: str = "1024x1024"
    default_quality: str = "high"
    timeout_seconds: int = 600
    # 提交模式：sync=同步等响应（默认，适配多数中转站）；async=202+task_id 轮询取图
    mode: Literal["sync", "async"] = "sync"
    task_query_path: str = ""
    poll_interval_seconds: int = Field(default=10, ge=1, le=120)
    extra_params: Optional[dict] = None
    param_options: Optional[dict] = None
    remark: str = ""

    @model_validator(mode="after")
    def _async_needs_query_path(self):
        if self.mode == "async" and not self.task_query_path.strip():
            raise ValueError("异步模式必须填写任务查询路径（如 /api/image-tasks）")
        return self
