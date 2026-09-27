from datetime import datetime
from typing import Optional

from sqlalchemy import (String, Text, Enum, Integer, BigInteger, DateTime,
                        ForeignKey, JSON, func, UniqueConstraint, Boolean)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

LIB = ("face", "outfit", "socks", "pose")

class Prompt(Base):
    __tablename__ = "prompt"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text().with_variant(MEDIUMTEXT(), "mysql"))
    tags: Mapped[str] = mapped_column(String(255), default="")
    remark: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class AssetGroup(Base):
    __tablename__ = "asset_group"
    __table_args__ = (
        UniqueConstraint("library", "name", name="uk_group_library_name"),
        {"mysql_charset": "utf8mb4"},
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    library: Mapped[str] = mapped_column(Enum(*LIB, name="library"))
    name: Mapped[str] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    images: Mapped[list["AssetImage"]] = relationship(back_populates="group", cascade="all, delete-orphan")

class AssetImage(Base):
    __tablename__ = "asset_image"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("asset_group.id", ondelete="CASCADE"))
    library: Mapped[str] = mapped_column(Enum(*LIB, name="library"))
    original_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    group: Mapped["AssetGroup"] = relationship(back_populates="images")

class Provider(Base):
    __tablename__ = "provider"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(Enum("openai", "mock"), default="openai")
    base_url: Mapped[str] = mapped_column(String(300), default="")
    api_key: Mapped[str] = mapped_column(String(300), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    gen_path: Mapped[str] = mapped_column(String(200), default="/v1/images/generations")
    edits_path: Mapped[str] = mapped_column(String(200), default="/v1/images/edits")
    image_field: Mapped[str] = mapped_column(String(50), default="image[]")
    default_model: Mapped[str] = mapped_column(String(100), default="gpt-image-1")
    default_size: Mapped[str] = mapped_column(String(30), default="1024x1024")
    default_quality: Mapped[str] = mapped_column(String(30), default="high")
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=600)
    # 提交模式：sync=同步等响应（多数中转站）；async=202+task_id 轮询取图（如噜皮）
    mode: Mapped[str] = mapped_column(Enum("sync", "async"), default="sync")
    task_query_path: Mapped[str] = mapped_column(String(200), default="")
    poll_interval_seconds: Mapped[int] = mapped_column(Integer, default=10)
    extra_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    param_options: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    remark: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class GenTask(Base):
    __tablename__ = "gen_task"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    prompt_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    prompt_name: Mapped[str] = mapped_column(String(100))
    prompt_content: Mapped[str] = mapped_column(Text().with_variant(MEDIUMTEXT(), "mysql"))
    provider_id: Mapped[int] = mapped_column(BigInteger)
    provider_name: Mapped[str] = mapped_column(String(100))
    endpoint: Mapped[str] = mapped_column(Enum("edits", "generations"))
    model: Mapped[str] = mapped_column(String(100))
    size: Mapped[str] = mapped_column(String(30))
    quality: Mapped[str] = mapped_column(String(30), default="")
    n: Mapped[int] = mapped_column(Integer, default=1)
    extra: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    assets: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(Enum("pending", "running", "success", "failed"), default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_dir: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # 异步源站返回的中转站任务 id（响应丢失时凭此到中转站后台/查询接口追回成果）
    remote_task_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    images: Mapped[list["TaskImage"]] = relationship(cascade="all, delete-orphan")

class TaskImage(Base):
    __tablename__ = "task_image"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("gen_task.id", ondelete="CASCADE"))
    file_path: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
