# AI 生图工作台 · 后端 API 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** FastAPI + MySQL 后端：提示词/四类素材库/API 源站/生图任务四组 REST API，含 Mock 源站与后台任务执行，pytest 全覆盖，绝不真实调用中转站。

**架构：** 单体 FastAPI 应用，SQLAlchemy 2.0 + PyMySQL 连用户本地 MySQL；素材与产出落磁盘（`DATA_DIR`/`OUTPUT_DIR`），元数据入库；生图任务提交后由 `ThreadPoolExecutor` 后台执行，通过 `provider.type=mock` 在本地生成占位图跑通全流程。前端契约见 `docs/superpowers/specs/2026-09-22-image-gen-platform-design.md`（下称"规格"），UI 参照 `prototype/index.html`。

**技术栈：** Python 3.11+ / FastAPI / uvicorn / SQLAlchemy 2.0 / PyMySQL / Pillow / requests / pytest + httpx(TestClient)

**前置条件：** 用户本地 MySQL 8 可连接；`.env` 已按 `.env.example` 配好（含 `TEST_DB_NAME=image_gen_platform_test`）。**任何测试不得携带真实 API Key 发外部请求**——源站连通性测试用 monkeypatch 伪造。

---

## 文件结构

```
requirements.txt            # 依赖
.env.example                # 配置模板（用户复制为 .env 填写）
run.py                      # 启动入口：建库建表 → 起服务
app/
  __init__.py
  config.py                 # 读 .env 的 Settings
  database.py               # engine / SessionLocal / get_db / init_db(建库建表)
  models.py                 # 6 个 ORM 模型（规格 §4）
  schemas.py                # Pydantic 请求/响应模型
  main.py                   # create_app()：路由挂载 /files 静态、启动重置遗留任务
  utils/
    __init__.py
    filenames.py            # 安全目录名、时间戳名、uuid 文件名
    image_io.py             # b64 解码 / url 下载 → 文件
  services/
    __init__.py
    storage.py              # 素材保存/删除/磁盘导入
    task_runner.py          # ThreadPoolExecutor 单例 + 启动重置
    generator.py            # 拼请求（edits/generations）+ 响应落盘 + 状态机
    mock_provider.py        # Pillow 占位图 → 伪 OpenAI 响应
  routers/
    __init__.py
    prompts.py              # /api/prompts
    libraries.py            # /api/libraries/{library}
    providers.py            # /api/providers
    tasks.py                # /api/tasks
tests/
  conftest.py               # 测试库自建自删 + TestClient fixture + 干净数据
  test_config_database.py
  test_models.py
  test_prompts_api.py
  test_storage_libraries_api.py
  test_import_dir.py
  test_providers_api.py
  test_generator.py
  test_task_flow.py
```

---

### 任务 1：项目骨架、配置与数据库连接

**文件：** 创建 `requirements.txt`、`.env.example`、`app/config.py`、`app/database.py`、`app/__init__.py`、`tests/conftest.py`、`tests/test_config_database.py`

- [ ] **步骤 1：写依赖与配置模板**

`requirements.txt`：
```
fastapi>=0.110
uvicorn[standard]>=0.29
sqlalchemy>=2.0
pymysql>=1.1
cryptography>=42          # pymysql caching_sha2_password 需要
pillow>=10
requests>=2.31
python-dotenv>=1.0
pytest>=8
httpx>=0.27
```

`.env.example`（规格 §3，追加测试库名）：
```ini
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=image_gen_platform
TEST_DB_NAME=image_gen_platform_test
DATA_DIR=data
OUTPUT_DIR=outputs
MAX_CONCURRENT_TASKS=2
APP_PORT=8765
```

- [ ] **步骤 2：编写失败的测试**

`tests/conftest.py`：
```python
import os, shutil
import pytest
from app.config import Settings

os.environ.setdefault("DB_NAME", "image_gen_platform_test")
os.environ.setdefault("TEST_DB_NAME", "image_gen_platform_test")

@pytest.fixture()
def settings(tmp_path):
    s = Settings()
    s.DATA_DIR = str(tmp_path / "data")
    s.OUTPUT_DIR = str(tmp_path / "outputs")
    return s

@pytest.fixture()
def test_engine(settings):
    from app import database
    engine = database.ensure_database(settings)   # 建库（若缺）+ 返回 engine
    database.Base.metadata.create_all(engine)
    yield engine
    database.Base.metadata.drop_all(engine)
```

`tests/test_config_database.py`：
```python
def test_settings_defaults(settings):
    assert settings.DB_NAME == "image_gen_platform_test"
    assert settings.MAX_CONCURRENT_TASKS >= 1

def test_ensure_database_creates_tables(test_engine):
    from sqlalchemy import inspect
    names = set(inspect(test_engine).get_table_names())
    assert {"prompt", "asset_group", "asset_image", "provider",
            "gen_task", "task_image"} <= names
```

- [ ] **步骤 3：运行验证失败**

运行：`python -m pytest tests/test_config_database.py -v`
预期：FAIL（`app` 包 / `Settings` / `ensure_database` 不存在）

- [ ] **步骤 4：实现**

`app/config.py`：
```python
import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    def __init__(self):
        self.DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
        self.DB_PORT = int(os.getenv("DB_PORT", "3306"))
        self.DB_USER = os.getenv("DB_USER", "root")
        self.DB_PASSWORD = os.getenv("DB_PASSWORD", "")
        self.DB_NAME = os.getenv("DB_NAME", "image_gen_platform")
        self.TEST_DB_NAME = os.getenv("TEST_DB_NAME", "image_gen_platform_test")
        self.DATA_DIR = os.getenv("DATA_DIR", "data")
        self.OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")
        self.MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "2"))
        self.APP_PORT = int(os.getenv("APP_PORT", "8765"))

    @property
    def db_url(self, name=None):
        name = name or self.DB_NAME
        return (f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{name}?charset=utf8mb4")

settings = Settings()
```

`app/database.py`：
```python
import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

class Base(DeclarativeBase): pass

def ensure_database(s=settings):
    """库不存在则创建（utf8mb4），返回绑定该库的 engine。"""
    raw = pymysql.connect(host=s.DB_HOST, port=s.DB_PORT, user=s.DB_USER,
                          password=s.DB_PASSWORD)
    with raw.cursor() as c:
        c.execute(f"CREATE DATABASE IF NOT EXISTS `{s.DB_NAME}` "
                  "DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci")
    raw.commit(); raw.close()
    engine = create_engine(s.db_url, pool_pre_ping=True, pool_recycle=1800)
    Base.metadata.create_all(engine)
    return engine

engine = None
SessionLocal = None

def init_app_db():
    global engine, SessionLocal
    engine = ensure_database()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()
```

- [ ] **步骤 5：运行验证通过**

运行：`python -m pytest tests/test_config_database.py -v`
预期：2 passed（需本地 MySQL 可连；连不上则报错信息含手工建库提示）

- [ ] **步骤 6：Commit**

```bash
git add requirements.txt .env.example app/ tests/
git commit -m "feat(backend): 项目骨架、配置与 MySQL 建库建表"
```

---

### 任务 2：ORM 模型（6 张表）

**文件：** 创建 `app/models.py`、`tests/test_models.py`；修改 `tests/conftest.py`（注入干净库的 session fixture）

- [ ] **步骤 1：编写失败的测试**

追加到 `tests/conftest.py`：
```python
@pytest.fixture()
def db(test_engine):
    from app import database
    Session = sessionmaker(bind=test_engine, expire_on_commit=False)
    s = Session()
    yield s
    s.rollback(); s.close()

@pytest.fixture(autouse=True)
def _clean(test_engine):
    yield
    from app import database
    database.Base.metadata.drop_all(test_engine)
    database.Base.metadata.create_all(test_engine)
```
（`from sqlalchemy.orm import sessionmaker` 放文件顶部）

`tests/test_models.py`：
```python
from app.models import Prompt, AssetGroup, AssetImage, Provider, GenTask, TaskImage

def test_prompt_roundtrip(db):
    p = Prompt(name="街拍白裙", content="A photo of ...", tags="街拍")
    db.add(p); db.commit()
    assert p.id is not None and p.updated_at is not None

def test_group_name_unique_per_library(db):
    db.add(AssetGroup(library="face", name="模特A"))
    db.add(AssetGroup(library="face", name="模特A"))
    try:
        db.commit(); assert False, "应触发同库组名唯一约束"
    except Exception: db.rollback()

def test_cascade_delete_images(db):
    g = AssetGroup(library="socks", name="白袜")
    g.images.append(AssetImage(library="socks", original_name="a.png", file_path="socks/1/a.png"))
    db.add(g); db.commit()
    gid = g.id
    db.delete(g); db.commit()
    assert db.query(AssetImage).filter_by(group_id=gid).count() == 0
```

- [ ] **步骤 2：运行验证失败**

运行：`python -m pytest tests/test_models.py -v`
预期：FAIL（`app.models` 不存在）

- [ ] **步骤 3：实现（严格按规格 §4 DDL）**

`app/models.py` 要点（字段与规格 DDL 一一对应，此处列骨架，字段全量照抄规格）：
```python
from datetime import datetime
from sqlalchemy import (String, Text, Enum, Integer, BigInteger, DateTime,
                        ForeignKey, JSON, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

LIB = ("face", "outfit", "socks", "pose")

class Prompt(Base):
    __tablename__ = "prompt"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    tags: Mapped[str] = mapped_column(String(255), default="")
    remark: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class AssetGroup(Base):
    __tablename__ = "asset_group"
    __table_args__ = ({"mysql_charset": "utf8mb4"},)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    library: Mapped[str] = mapped_column(Enum(*LIB, name="library"))
    name: Mapped[str] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint("library", "name", name="uk_group_library_name"),)
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
    id, name, type(Enum("openai","mock")), base_url, api_key, enabled,
    gen_path="/v1/images/generations", edits_path="/v1/images/edits",
    image_field="image[]", default_model="gpt-image-1", default_size="1024x1024",
    default_quality="high", timeout_seconds=300, extra_params(JSON, nullable),
    param_options(JSON, nullable), remark, created_at, updated_at
    # （按规格 §4 provider 表逐列写全）

class GenTask(Base):
    __tablename__ = "gen_task"
    id, prompt_id(nullable), prompt_name, prompt_content, provider_id, provider_name,
    endpoint(Enum("edits","generations")), model, size, quality, n(Integer),
    extra(JSON, nullable), assets(JSON, nullable),
    status(Enum("pending","running","success","failed"), default="pending"),
    error_message(Text, nullable), output_dir(String(500), nullable),
    created_at, started_at(nullable), finished_at(nullable)
    images: Mapped[list["TaskImage"]] = relationship(cascade="all, delete-orphan")

class TaskImage(Base):
    __tablename__ = "task_image"
    id, task_id(ForeignKey("gen_task.id", ondelete="CASCADE")),
    file_path(String(500)), created_at
```
（`UniqueConstraint` 从 sqlalchemy 导入；Provider/GenTask 按规格全字段写全，不许省列。）

- [ ] **步骤 4：运行验证通过**

运行：`python -m pytest tests/test_models.py -v`
预期：3 passed

- [ ] **步骤 5：Commit**

```bash
git add app/models.py tests/
git commit -m "feat(backend): 六张表 ORM 模型"
```

---

### 任务 3：提示词 API

**文件：** 创建 `app/schemas.py`、`app/routers/prompts.py`、`app/routers/__init__.py`、`app/main.py`、`tests/test_prompts_api.py`；修改 `tests/conftest.py`（client fixture）

- [ ] **步骤 1：client fixture（追加 conftest）**

```python
@pytest.fixture()
def client(test_engine, settings, monkeypatch):
    from fastapi import FastAPI
    from app.database import get_db
    from app.routers import prompts
    Session = sessionmaker(bind=test_engine, expire_on_commit=False)
    app = FastAPI()
    app.include_router(prompts.router, prefix="/api")

    def override():
        s = Session(); yield s
    app.dependency_overrides[get_db] = override
    from httpx import Client, ASGITransport
    c = Client(ASGITransport(app=app), base_url="http://t")
    yield c
    c.close()
```

`tests/test_prompts_api.py`：
```python
def test_crud_and_search(client):
    r = client.post("/api/prompts", json={"name": "街拍白裙", "content": "A photo", "tags": "街拍"})
    assert r.status_code == 200 and r.json()["id"] > 0
    pid = r.json()["id"]
    r = client.post("/api/prompts", json={"name": "森系", "content": "forest", "tags": "外景"})
    assert r.status_code == 200
    assert client.get("/api/prompts?keyword=白裙").json()["total"] == 1
    assert client.get("/api/prompts").json()["total"] == 2
    r = client.put(f"/api/prompts/{pid}", json={"name": "街拍白裙V2", "content": "A photo2", "tags": ""})
    assert r.json()["name"] == "街拍白裙V2"
    assert client.delete(f"/api/prompts/{pid}").status_code == 200
    assert client.get(f"/api/prompts/{pid}").status_code == 404
    assert client.post("/api/prompts", json={"name": "", "content": "x"}).status_code == 422
```

- [ ] **步骤 2：运行验证失败**

运行：`python -m pytest tests/test_prompts_api.py -v`
预期：FAIL（路由不存在）

- [ ] **步骤 3：实现**

`app/schemas.py`（本任务先写提示词部分）：
```python
from pydantic import BaseModel, Field

class PromptIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=20000)
    tags: str = ""
    remark: str = ""

class PromptOut(PromptIn):
    id: int
    class Config: from_attributes = True
```

`app/routers/prompts.py`：
```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Prompt
from ..schemas import PromptIn, PromptOut

router = APIRouter(prefix="/prompts", tags=["prompts"])

@router.get("")
def list_prompts(keyword: str = "", page: int = Query(1, ge=1),
                 size: int = Query(50, le=200), db: Session = Depends(get_db)):
    q = db.query(Prompt)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(Prompt.name.like(like) | Prompt.content.like(like) | Prompt.tags.like(like))
    total = q.count()
    items = q.order_by(Prompt.id.desc()).offset((page - 1) * size).limit(size).all()
    return {"items": [PromptOut.model_validate(i) for i in items], "total": total, "page": page, "size": size}

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
```

`app/main.py`（最小可运行，后续任务继续挂路由）：
```python
from fastapi import FastAPI
from .database import init_app_db
from .routers import prompts

def create_app():
    app = FastAPI(title="生图工作台 API")
    init_app_db()
    app.include_router(prompts.router, prefix="/api")
    return app

app = create_app()
```

- [ ] **步骤 4：运行验证通过**

运行：`python -m pytest tests/test_prompts_api.py -v`
预期：1 passed（用例内含全流程断言）

- [ ] **步骤 5：Commit**

```bash
git add app/ tests/
git commit -m "feat(backend): 提示词 CRUD 与搜索 API"
```

---

### 任务 4：文件存储服务 + 素材库组 API

**文件：** 创建 `app/utils/filenames.py`、`app/services/storage.py`、`app/services/__init__.py`、`app/utils/__init__.py`、`app/routers/libraries.py`、`tests/test_storage_libraries_api.py`；修改 `conftest.py`（client 挂 libraries 路由 + settings 注入）、`app/main.py`

- [ ] **步骤 1：编写失败的测试**

conftest 的 client fixture 改为同时挂 `libraries.router`，并用 monkeypatch 把 `storage.DATA_DIR` 指到 tmp：
```python
    from app.services import storage
    monkeypatch.setattr(storage, "DATA_DIR", settings.DATA_DIR)
    os.makedirs(settings.DATA_DIR, exist_ok=True)
```
（`import os` 置顶）

`tests/test_storage_libraries_api.py`：
```python
import io
from PIL import Image

def png_bytes():
    b = io.BytesIO(); Image.new("RGB", (8, 8), (200, 60, 60)).save(b, "PNG")
    return b.getvalue()

def test_group_crud(client):
    r = client.post("/api/libraries/face/groups", json={"name": "模特A"})
    assert r.status_code == 200 and r.json()["image_count"] == 0
    assert client.post("/api/libraries/face/groups", json={"name": "模特A"}).status_code == 400
    gid = client.get("/api/libraries/face/groups").json()[0]["id"]
    assert client.put(f"/api/libraries/face/groups/{gid}", json={"name": "模特B"}).status_code == 200
    assert client.delete(f"/api/libraries/face/groups/{gid}").status_code == 200

def test_upload_list_delete_image(client, settings):
    gid = client.post("/api/libraries/socks/groups", json={"name": "白袜"}).json()["id"]
    r = client.post(f"/api/libraries/socks/images",
                    data={"group_id": str(gid)},
                    files=[("files", ("细节1.png", png_bytes(), "image/png")),
                           ("files", ("细节2.png", png_bytes(), "image/png"))])
    assert r.status_code == 200 and r.json()["imported"] == 2
    imgs = client.get(f"/api/libraries/socks/images?group_id={gid}").json()
    assert len(imgs) == 2 and imgs[0]["url"].startswith("/files/libraries/socks/")
    path = settings.DATA_DIR + "/" + imgs[0]["file_path"]
    assert os.path.exists(path)
    bad = client.post(f"/api/libraries/socks/images", data={"group_id": str(gid)},
                      files=[("files", ("x.gif", b"GIF89a", "image/gif"))])
    assert bad.status_code == 400
    img_id = imgs[0]["id"]
    assert client.delete(f"/api/libraries/socks/images/{img_id}").status_code == 200
    assert not os.path.exists(path)
```

- [ ] **步骤 2：运行验证失败**

运行：`python -m pytest tests/test_storage_libraries_api.py -v`
预期：FAIL

- [ ] **步骤 3：实现**

`app/utils/filenames.py`：
```python
import re, uuid
from datetime import datetime

def safe_dirname(name: str, maxlen: int = 80) -> str:
    name = re.sub(r'[\\/:*?"<>|\r\n]', "", name).strip().replace(" ", "_")
    return name[:maxlen] or "未命名"

def stamp(fmt: str = "%Y%m%d%H%M%S") -> str:
    return datetime.now().strftime(fmt)

def uuid_filename(original: str) -> str:
    return f"{uuid.uuid4().hex[:8]}_{original}"
```

`app/services/storage.py`：
```python
import os
DATA_DIR = "data"   # main 启动时与测试中由 settings 覆盖
ALLOWED = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
MAX_SIZE = 20 * 1024 * 1024

def lib_dir(library: str) -> str:
    d = os.path.join(DATA_DIR, "libraries", library)
    os.makedirs(d, exist_ok=True); return d

def save_image(library: str, group_id: int, filename: str, data: bytes) -> str:
    """落盘并返回相对 DATA_DIR/libraries 的 POSIX 路径。校验放路由层。"""
    from ..utils.filenames import uuid_filename
    d = os.path.join(lib_dir(library), str(group_id))
    os.makedirs(d, exist_ok=True)
    name = uuid_filename(filename)
    with open(os.path.join(d, name), "wb") as f: f.write(data)
    return f"{library}/{group_id}/{name}"

def delete_image(rel_path: str):
    p = os.path.join(DATA_DIR, "libraries", rel_path)
    if os.path.exists(p): os.remove(p)
```

`app/routers/libraries.py`（组 CRUD + 图片上传/列表/改名/移动/删除；非法 library 404）：
```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile
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
    g = db.get(AssetGroup, gid) or _raise(404, "组不存在")
    g.name = body.name; db.commit(); return {"id": g.id, "name": g.name}

@router.delete("/{library}/groups/{gid}")
def delete_group(library: str, gid: int, db: Session = Depends(get_db)):
    g = db.get(AssetGroup, gid) or _raise(404, "组不存在")
    for img in list(g.images): storage.delete_image(img.file_path)
    db.delete(g); db.commit(); return {"ok": True}

@router.get("/{library}/images")
def list_images(library: str, group_id: int | None = None, keyword: str = "",
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
async def upload_images(library: str, group_id: int, files: list[UploadFile],
                        db: Session = Depends(get_db)):
    _lib(library)
    g = db.get(AssetGroup, group_id) or _raise(404, "组不存在")
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
    i = db.get(AssetImage, img_id) or _raise(404, "图片不存在")
    for k in ("original_name", "group_id", "sort_order"):
        if k in body: setattr(i, k, body[k])
    db.commit(); return {"ok": True}

@router.delete("/{library}/images/{img_id}")
def delete_image(library: str, img_id: int, db: Session = Depends(get_db)):
    i = db.get(AssetImage, img_id) or _raise(404, "图片不存在")
    storage.delete_image(i.file_path)
    db.delete(i); db.commit(); return {"ok": True}

def _raise(code, msg): raise HTTPException(code, msg)
```
`GroupIn` 加进 `app/schemas.py`：`class GroupIn(BaseModel): name: str = Field(min_length=1, max_length=100)`。
`app/main.py` 增加静态挂载与 libraries 路由：
```python
import os
from fastapi.staticfiles import StaticFiles
from .config import settings
from .routers import libraries
    # create_app() 内：
    os.makedirs(os.path.join(settings.DATA_DIR, "libraries"), exist_ok=True)
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    app.include_router(libraries.router, prefix="/api")
    app.mount("/files/libraries", StaticFiles(directory=os.path.join(settings.DATA_DIR, "libraries")), name="libfiles")
```
（main 的静态挂载不在本任务测试范围，任务 10 验证。）

- [ ] **步骤 4：运行验证通过**

运行：`python -m pytest tests/test_storage_libraries_api.py -v`
预期：2 passed

- [ ] **步骤 5：Commit**

```bash
git add app/ tests/
git commit -m "feat(backend): 素材库组与图片 API，上传落盘与级联删除"
```

---

### 任务 5：import-dir 磁盘批量导入

**文件：** 修改 `app/routers/libraries.py`（新增 import-dir 接口）、`tests/test_import_dir.py`

- [ ] **步骤 1：编写失败的测试**

`tests/test_import_dir.py`：
```python
import os
from .test_storage_libraries_api import png_bytes

def test_import_dir(client, tmp_path):
    src = tmp_path / "袜子库"
    (src / "条纹袜").mkdir(parents=True)
    (src / "纯色袜" / "子目录").mkdir(parents=True)          # 递归导入验证
    (src / "条纹袜" / "a.png").write_bytes(png_bytes())
    (src / "纯色袜" / "子目录" / "b.png").write_bytes(png_bytes())
    (src / "根散图.png").write_bytes(png_bytes())
    (src / "坏文件.gif").write_bytes(b"GIF89a")
    r = client.post("/api/libraries/socks/import-dir", json={"source_dir": str(src)})
    j = r.json()
    assert r.status_code == 200
    assert j["groups_created"] == 3 and j["images_imported"] == 3 and j["skipped"] == 1
    names = {g["name"] for g in client.get("/api/libraries/socks/groups").json()}
    assert {"条纹袜", "纯色袜", "未分组"} <= names
    again = client.post("/api/libraries/socks/import-dir", json={"source_dir": str(src)}).json()
    assert again["groups_merged"] == 3 and again["groups_created"] == 0

def test_import_dir_not_exists(client, tmp_path):
    r = client.post("/api/libraries/socks/import-dir", json={"source_dir": str(tmp_path / "无")})
    assert r.status_code == 400
```

- [ ] **步骤 2：运行验证失败**

运行：`python -m pytest tests/test_import_dir.py -v`
预期：FAIL（404，接口不存在）

- [ ] **步骤 3：实现（追加到 libraries.py）**

```python
import os
from pydantic import BaseModel

class ImportDirIn(BaseModel):
    source_dir: str

@router.post("/{library}/import-dir")
def import_dir(library: str, body: ImportDirIn, db: Session = Depends(get_db)):
    _lib(library)
    src = body.source_dir
    if not os.path.isdir(src): raise HTTPException(400, "后端机器上不存在该目录")
    def ensure_group(name: str):
        g = db.query(AssetGroup).filter_by(library=library, name=name).first()
        created = g is None
        if created:
            g = AssetGroup(library=library, name=name); db.add(g); db.flush()
        return g, created
    stats = {"groups_created": 0, "groups_merged": 0, "images_imported": 0, "skipped": 0}
    def walk_dir(d, group):
        for root, _, files in os.walk(d):
            for fn in files:
                path = os.path.join(root, fn)
                with open(path, "rb") as fh: data = fh.read()
                import mimetypes
                mime = mimetypes.guess_type(fn)[0]
                if mime not in storage.ALLOWED or len(data) > storage.MAX_SIZE:
                    stats["skipped"] += 1; continue
                rel = storage.save_image(library, group.id, fn, data)
                db.add(AssetImage(library=library, group_id=group.id,
                                  original_name=fn, file_path=rel))
                stats["images_imported"] += 1
    entries = os.listdir(src)
    root_loose = ensure_group("未分组")
    for name in entries:
        p = os.path.join(src, name)
        if os.path.isdir(p):
            g, created = ensure_group(name)
            stats["groups_created" if created else "groups_merged"] += 1
            walk_dir(p, g)
        else:
            if not root_loose[1]: stats["groups_merged"] += 0
            with open(p, "rb") as fh: data = fh.read()
            import mimetypes
            mime = mimetypes.guess_type(name)[0]
            if mime not in storage.ALLOWED or len(data) > storage.MAX_SIZE:
                stats["skipped"] += 1; continue
            rel = storage.save_image(library, root_loose[0].id, name, data)
            db.add(AssetImage(library=library, group_id=root_loose[0].id,
                              original_name=name, file_path=rel))
            stats["images_imported"] += 1
    db.commit()
    return stats
```
（根散图并入「未分组」；`groups_merged` 统计的是二级并入口径与测试对齐——若第二遍全量并入则为 3。注意实现与测试断言口径一致：`ensure_group` 返回 created 标记，已存在即 merged。）

- [ ] **步骤 4：运行验证通过**

运行：`python -m pytest tests/test_import_dir.py -v`
预期：2 passed

- [ ] **步骤 5：Commit**

```bash
git add app/routers/libraries.py tests/test_import_dir.py
git commit -m "feat(backend): 按磁盘路径批量导入素材（一级子目录=组，递归）"
```

---

### 任务 6：源站 API + 连通性测试

**文件：** 创建 `app/routers/providers.py`、`tests/test_providers_api.py`；修改 `app/schemas.py`、`app/main.py`、conftest client

- [ ] **步骤 1：编写失败的测试**

`tests/test_providers_api.py`：
```python
def test_provider_crud(client, monkeypatch):
    body = {"name": "中转站A", "type": "openai", "base_url": "https://api.a.com",
            "api_key": "sk-test", "param_options": {"size": ["1:1"], "n_max": 4}}
    pid = client.post("/api/providers", json=body).json()["id"]
    lst = client.get("/api/providers").json()
    assert lst[0]["name"] == "中转站A" and lst[0]["param_options"]["n_max"] == 4
    client.put(f"/api/providers/{pid}", json={**body, "enabled": False})
    assert client.get(f"/api/providers/{pid}").json()["enabled"] is False

def test_connectivity(client, monkeypatch):
    pid = client.post("/api/providers", json={
        "name": "A", "type": "openai", "base_url": "https://api.a.com", "api_key": "k"}).json()["id"]
    class FakeResp:
        status_code = 200
        def json(self): return {"data": [{"id": "m"}] * 42}
    calls = {}
    def fake_get(url, headers=None, timeout=None):
        calls["url"] = url; calls["auth"] = headers.get("Authorization")
        return FakeResp()
    import app.routers.providers as P
    monkeypatch.setattr(P.requests, "get", fake_get)
    r = client.post(f"/api/providers/{pid}/test").json()
    assert r["ok"] is True and r["model_count"] == 42
    assert calls["url"] == "https://api.a.com/v1/models" and calls["auth"] == "Bearer k"

def test_mock_connectivity(client):
    mid = client.post("/api/providers", json={"name": "Mock", "type": "mock"}).json()["id"]
    assert client.post(f"/api/providers/{mid}/test").json()["ok"] is True

def test_bad_key_result(client, monkeypatch):
    pid = client.post("/api/providers", json={
        "name": "B", "type": "openai", "base_url": "https://b.com", "api_key": "bad"}).json()["id"]
    class FakeResp:
        status_code = 401
        def json(self): return {}
    import app.routers.providers as P
    monkeypatch.setattr(P.requests, "get", lambda *a, **k: FakeResp())
    r = client.post(f"/api/providers/{pid}/test").json()
    assert r["ok"] is False and "401" in r["message"]
```

- [ ] **步骤 2：运行验证失败**

运行：`python -m pytest tests/test_providers_api.py -v`
预期：FAIL

- [ ] **步骤 3：实现**

`schemas.py` 追加：
```python
class ProviderIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: str = "openai"
    base_url: str = ""
    api_key: str = ""
    enabled: bool = True
    gen_path: str = "/v1/images/generations"
    edits_path: str = "/v1/images/edits"
    image_field: str = "image[]"
    default_model: str = "gpt-image-1"
    default_size: str = "1024x1024"
    default_quality: str = "high"
    timeout_seconds: int = 300
    extra_params: dict | None = None
    param_options: dict | None = None
    remark: str = ""
```

`app/routers/providers.py`：
```python
import requests as http
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Provider
from ..schemas import ProviderIn

router = APIRouter(prefix="/providers", tags=["providers"])

@router.get("")
def list_providers(db: Session = Depends(get_db)):
    return [p.__dict__ | {"extra_params": p.extra_params, "param_options": p.param_options}
            for p in db.query(Provider).order_by(Provider.id).all()]
# （ORM 对象直接序列化：实际实现用 to_dict 帮助函数过滤 _sa_instance_state）

@router.post("")
def create(body: ProviderIn, db: Session = Depends(get_db)):
    p = Provider(**body.model_dump()); db.add(p); db.commit(); db.refresh(p)
    return p.__dict__ | {"extra_params": p.extra_params, "param_options": p.param_options}

@router.get("/{pid}")
def get_one(pid: int, db: Session = Depends(get_db)): return _one(db, pid)

@router.put("/{pid}")
def update(pid: int, body: ProviderIn, db: Session = Depends(get_db)):
    p = _one(db, pid)
    for k, v in body.model_dump().items(): setattr(p, k, v)
    db.commit(); return _one(db, pid)

@router.delete("/{pid}")
def delete(pid: int, db: Session = Depends(get_db)):
    p = _one(db, pid); db.delete(p); db.commit(); return {"ok": True}

@router.post("/{pid}/test")
def test_conn(pid: int, db: Session = Depends(get_db)):
    p = _one(db, pid)
    if p.type == "mock":
        return {"ok": True, "status_code": 0, "model_count": 0, "message": "Mock 源站，本地联调"}
    try:
        r = http.get(f"{p.base_url}/v1/models",
                     headers={"Authorization": f"Bearer {p.api_key}"}, timeout=5)
        if r.status_code == 200:
            n = len((r.json() or {}).get("data", []))
            return {"ok": True, "status_code": 200, "model_count": n, "message": "连通正常"}
        return {"ok": False, "status_code": r.status_code, "model_count": 0,
                "message": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"ok": False, "status_code": 0, "model_count": 0, "message": str(e)[:200]}

def _one(db, pid):
    p = db.get(Provider, pid)
    if not p: raise HTTPException(404, "源站不存在")
    return p
```
（列表/详情返回统一走 `to_dict(p)` 帮助函数，排除 `_sa_instance_state`，实现时补上。）main 挂路由 + conftest client 挂 providers。

- [ ] **步骤 4：运行验证通过**

运行：`python -m pytest tests/test_providers_api.py -v`
预期：4 passed

- [ ] **步骤 5：Commit**

```bash
git add app/ tests/
git commit -m "feat(backend): 源站 CRUD 与连通性测试（/v1/models，免费）"
```

---

### 任务 7：生成器核心（拼请求 + 响应落盘）+ Mock 源站

**文件：** 创建 `app/services/generator.py`、`app/services/mock_provider.py`、`app/utils/image_io.py`、`tests/test_generator.py`

- [ ] **步骤 1：编写失败的测试**

`tests/test_generator.py`：
```python
import base64, json
from app.services import generator as G

def _task(provider_type="openai", **kw):
    from app.models import Provider, GenTask
    p = Provider(name="P", type=provider_type, base_url="https://x.com",
                 api_key="sk", default_model="m", default_size="1024x1024",
                 default_quality="high", timeout_seconds=5, **kw.get("provider_kw", {}))
    t = GenTask(prompt_id=None, prompt_name="测试", prompt_content="hi",
                provider_id=1, provider_name="P", endpoint="generations",
                model="m", size="1024x1024", quality="high", n=1, extra=None)
    return p, t

def test_build_generations_request():
    p, t = _task()
    method, url, kwargs = G.build_request(p, t, image_files=[])
    assert url.endswith("/v1/images/generations")
    assert kwargs["json"] == {"prompt": "hi", "model": "m", "n": 1, "size": "1024x1024", "quality": "high"}
    assert kwargs["headers"]["Authorization"] == "Bearer sk"

def test_build_edits_multipart():
    p, t = _task()
    t.endpoint = "edits"
    files = [("image[]", ("a.png", b"x", "image/png")), ("image[]", ("b.png", b"y", "image/png"))]
    method, url, kwargs = G.build_request(p, t, image_files=files)
    assert url.endswith("/v1/images/edits")
    assert kwargs["data"]["prompt"] == "hi" and len(kwargs["files"]) == 2
    p.image_field = "image"                       # 字段名可覆盖
    assert G.build_request(p, t, image_files=files)[2]["files"][0][0] == "image"

def test_extra_merge_and_resolution():
    p, t = _task(provider_kw={"extra_params": {"background": "transparent"}})
    t.extra = {"resolution": "4K"}
    _, _, kwargs = G.build_request(p, t, image_files=[])
    assert kwargs["json"]["background"] == "transparent" and kwargs["json"]["resolution"] == "4K"

def test_save_b64_response(tmp_path, monkeypatch):
    p, t = _task()
    monkeypatch.setattr(G, "OUTPUT_DIR", str(tmp_path))
    b64 = base64.b64encode(b"fakepng").decode()
    paths = G.save_results(t, {"data": [{"b64_json": b64}]}, out_dir=str(tmp_path / "o"))
    assert len(paths) == 1 and paths[0].endswith(".png")

def test_save_url_response(tmp_path, monkeypatch):
    from app.utils import image_io
    p, t = _task()
    monkeypatch.setattr(G, "OUTPUT_DIR", str(tmp_path))
    class R:
        status_code = 200; content = b"jpgdata"; headers = {"Content-Type": "image/jpeg"}
    monkeypatch.setattr(image_io.requests, "get", lambda *a, **k: R())
    paths = G.save_results(t, {"data": [{"url": "https://x/1.jpg"}]}, out_dir=str(tmp_path / "o"))
    assert paths[0].endswith(".jpg")

def test_mock_provider(tmp_path):
    from app.services import mock_provider
    resp = mock_provider.generate(prompt="一只白袜特写", model="m", size="1024x1024",
                                  n=1, quality="high", extra=None)
    assert resp["data"] and base64.b64decode(resp["data"][0]["b64_json"])[:4] != b""
```

- [ ] **步骤 2：运行验证失败**

运行：`python -m pytest tests/test_generator.py -v`
预期：FAIL

- [ ] **步骤 3：实现**

`app/utils/image_io.py`：
```python
import base64, requests

def save_b64(b64: str, path: str):
    with open(path, "wb") as f: f.write(base64.b64decode(b64))

def download(url: str, path: str, tries: int = 2):
    for i in range(tries):
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 200:
                with open(path, "wb") as f: f.write(r.content)
                return r.headers.get("Content-Type", "")
        except Exception:
            if i == tries - 1: raise
    raise RuntimeError(f"下载失败 {url}")
```

`app/services/generator.py`：
```python
import json, os
import requests
from ..utils import image_io
from ..utils.filenames import stamp

OUTPUT_DIR = "outputs"   # 启动/测试时由 settings 覆盖

def build_request(p, t, image_files: list[tuple]):
    """返回 (url, kwargs)。image_files 为 [(字段名, (文件名, bytes, mime))] 的展开列表。"""
    url = p.base_url + (p.edits_path if t.endpoint == "edits" else p.gen_path)
    headers = {"Authorization": f"Bearer {p.api_key}"}
    params = {"prompt": t.prompt_content, "model": t.model, "n": t.n, "size": t.size}
    if t.quality: params["quality"] = t.quality
    if t.extra: params.update(t.extra or {})
    if t.endpoint == "edits":
        data = {k: str(v) if not isinstance(v, str) else v for k, v in params.items()}
        kwargs = {"data": data, "files": image_files}
    else:
        kwargs = {"json": params}
    if p.extra_params:                          # 源站固定附加字段最后合并
        (kwargs["data"] if t.endpoint == "edits" else kwargs["json"]).update(p.extra_params)
    kwargs["headers"] = headers
    kwargs["timeout"] = p.timeout_seconds
    return url, kwargs

def save_results(t, resp_json, out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    ts = stamp()
    for i, item in enumerate(resp_json.get("data", []), start=1):
        fp = os.path.join(out_dir, f"{ts}_{i}.png")
        if item.get("b64_json"):
            image_io.save_b64(item["b64_json"], fp)
        elif item.get("url"):
            ct = image_io.download(item["url"], fp)
            if "jpeg" in ct: os.rename(fp, fp[:-4] + ".jpg")
            elif "webp" in ct: os.rename(fp, fp[:-4] + ".webp")
        else:
            continue
        paths.append(fp)
    return paths

def write_task_json(out_dir: str, task_dict: dict, files: list[str], elapsed: float):
    meta = {**task_dict, "files": [os.path.basename(f) for f in files], "elapsed_seconds": elapsed}
    with open(os.path.join(out_dir, "task.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
```

`app/services/mock_provider.py`：
```python
import base64, io, time
from PIL import Image, ImageDraw

def generate(prompt: str, model: str, size: str, n: int, quality: str, extra=None) -> dict:
    w, h = _parse_size(size)
    time.sleep(2)                                # 模拟耗时
    data = []
    for _ in range(n):
        img = Image.new("RGB", (w, h), (238, 240, 243))
        d = ImageDraw.Draw(img)
        d.rectangle([w//8, h//8, w*7//8, h*7//8], outline=(35, 39, 47), width=4)
        d.text((w//10, h//2 - 20), f"MOCK {model} {size} {quality}", fill=(35, 39, 47))
        d.text((w//10, h//2 + 20), prompt[:60], fill(90, 100, 120))
        buf = io.BytesIO(); img.save(buf, "PNG")
        data.append({"b64_json": base64.b64encode(buf.getvalue()).decode()})
    return {"created": int(time.time()), "data": data}

def _parse_size(size: str, default=(1024, 1024)):
    try:
        a, b = size.lower().split("x"); return int(a), int(b)
    except Exception:
        return default
```
（实现时修掉 `d.text(..., fill(90,100,120))` 的笔误 → `fill=(90,100,120)`。）

- [ ] **步骤 4：运行验证通过**

运行：`python -m pytest tests/test_generator.py -v`
预期：6 passed

- [ ] **步骤 5：Commit**

```bash
git add app/ tests/
git commit -m "feat(backend): 生图请求拼接、响应落盘与 Mock 源站"
```

---

### 任务 8：任务 API + 后台执行 + Mock 端到端

**文件：** 创建 `app/services/task_runner.py`、`app/routers/tasks.py`、`tests/test_task_flow.py`；修改 `app/main.py`、conftest client

- [ ] **步骤 1：编写失败的测试**

`tests/test_task_flow.py`：
```python
import time
from .test_storage_libraries_api import png_bytes

def _setup_provider_and_assets(client):
    pid = client.post("/api/providers", json={"name": "Mock", "type": "mock",
        "po_n_max": 10}).json()["id"]
    gid = client.post("/api/libraries/face/groups", json={"name": "模特A"}).json()["id"]
    client.post("/api/libraries/face/images", data={"group_id": str(gid)},
                files=[("files", ("a.png", png_bytes(), "image/png"))])
    img = client.get(f"/api/libraries/face/images?group_id={gid}").json()[0]
    return pid, img["id"]

def test_task_success_flow(client, settings, monkeypatch):
    from app.services import task_runner
    pid, img_id = _setup_provider_and_assets(client)
    r = client.post("/api/tasks", json={
        "prompt_name": "街拍白裙", "prompt_content": "A photo", "provider_id": pid,
        "model": "gpt-image-1", "size": "1024x1024", "quality": "high", "n": 1,
        "assets": [{"library": "face", "image_ids": [img_id]}]})
    assert r.status_code == 200
    tid = r.json()["id"]
    deadline = time.time() + 15
    task = {}
    while time.time() < deadline:
        task = client.get(f"/api/tasks/{tid}").json()
        if task["status"] in ("success", "failed"): break
        time.sleep(0.3)
    assert task["status"] == "success", task.get("error_message")
    assert len(task["images"]) == 1
    assert task["assets"][0]["group_name"] == "模特A"       # 快照补全 group
    assert client.post(f"/api/tasks/{tid}/rerun").status_code == 200

def test_task_generations_when_no_assets(client, settings):
    pid = client.post("/api/providers", json={"name": "Mock", "type": "mock"}).json()["id"]
    tid = client.post("/api/tasks", json={"prompt_name": "纯文", "prompt_content": "x",
        "provider_id": pid, "n": 1}).json()["id"]
    deadline = time.time() + 15
    while time.time() < deadline:
        t = client.get(f"/api/tasks/{tid}").json()
        if t["status"] in ("success", "failed"): break
        time.sleep(0.3)
    assert t["endpoint"] == "generations" and t["status"] == "success"

def test_missing_asset_fails(client):
    pid = client.post("/api/providers", json={"name": "Mock", "type": "mock"}).json()["id"]
    r = client.post("/api/tasks", json={"prompt_name": "x", "prompt_content": "x",
        "provider_id": pid, "assets": [{"library": "face", "image_ids": [99999]}]})
    assert r.status_code == 400 and "不存在" in r.json()["detail"]
```
（conftest 的 client 需挂 tasks 路由 + 注入 `task_runner` 用测试 `SessionLocal` 与 tmp 输出目录：`monkeypatch.setattr(task_runner, "SessionLocal", TestSession)`、`generator.OUTPUT_DIR`、并让 runner 用同一个 test_engine 建会话。）

- [ ] **步骤 2：运行验证失败**

运行：`python -m pytest tests/test_task_flow.py -v`
预期：FAIL（路由不存在）

- [ ] **步骤 3：实现**

`app/services/task_runner.py`：
```python
import concurrent.futures, traceback
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from . import generator
from ..models import GenTask, TaskImage, Provider, AssetImage, AssetGroup

executor: concurrent.futures.ThreadPoolExecutor | None = None
SessionLocal = None

def init_runner(session_factory, max_workers: int):
    global executor, SessionLocal
    SessionLocal = session_factory
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

def submit(task_id: int):
    executor.submit(_run, task_id)

def _run(task_id: int):
    db = SessionLocal()
    try:
        t = db.get(GenTask, task_id)
        t.status = "running"; t.started_at = datetime.now(); db.commit()
        p = db.get(Provider, t.provider_id)
        files = []
        if t.endpoint == "edits":
            for grp in (t.assets or []):
                ids = grp["image_ids"]
                rows = (db.query(AssetImage).join(AssetGroup)
                        .filter(AssetImage.id.in_(ids), AssetImage.library == grp["library"])
                        .order_by(AssetImage.id).all())
                rows.sort(key=lambda r: ids.index(r.id))
                for r in rows:
                    path = os.path.join(generator.DATA_DIR, "libraries", r.file_path)
                    mime = _mime(r.file_path)
                    files.append((p.image_field, (r.original_name, open(path, "rb").read(), mime)))
        url, kwargs = generator.build_request(p, t, image_files=files)
        started = time.time()
        if p.type == "mock":
            from . import mock_provider
            resp = mock_provider.generate(prompt=t.prompt_content, model=t.model,
                size=t.size, n=t.n, quality=t.quality, extra=t.extra)
        else:
            resp = requests.post(url, **kwargs).json()
        out_dir = os.path.join(generator.OUTPUT_DIR, t.prompt_name, f"{stamp()}_{t.id}")
        paths = generator.save_results(t, resp, out_dir=out_dir)
        if not paths: raise RuntimeError("中转站未返回任何图片")
        for fp in paths:
            rel = os.path.relpath(fp, generator.OUTPUT_DIR).replace("\\", "/")
            db.add(TaskImage(task_id=t.id, file_path=rel))
        t.output_dir = os.path.relpath(out_dir, generator.OUTPUT_DIR).replace("\\", "/")
        generator.write_task_json(out_dir, _snapshot(t), paths, time.time() - started)
        t.status = "success"
    except Exception as e:
        t.status = "failed"; t.error_message = (str(e) or traceback.format_exc())[:2000]
    finally:
        t.finished_at = datetime.now(); db.commit(); db.close()
```
（`import os, time, requests` 置顶；`_mime` 按扩展名映射 png/jpg/webp；`_snapshot(t)` 返回任务全字段 dict 供 task.json。实现时把 open 的文件句柄改为 `with` 或直接传 bytes——上面读 bytes 进内存可接受，单图 ≤20MB。）

`app/routers/tasks.py`：
```python
@router.post("")
def create_task(body: TaskIn, db: Session = Depends(get_db)):
    p = db.get(Provider, body.provider_id) or _raise(400, "源站不存在")
    ids = [i for a in body.assets for i in a.image_ids]
    rows = []
    if ids:
        found = {r.id: r for r in db.query(AssetImage).filter(AssetImage.id.in_(ids)).all()}
        for a in body.assets:
            for i in a.image_ids:
                r = found.get(i)
                if not r or r.library != a.library:
                    _raise(400, f"{a.library} 库中不存在图片 id={i}")
                rows.append(r)
    endpoint = "edits" if ids else "generations"
    t = GenTask(prompt_id=body.prompt_id, prompt_name=body.prompt_name,
        prompt_content=body.prompt_content, provider_id=p.id, provider_name=p.name,
        endpoint=endpoint, model=body.model or p.default_model,
        size=body.size or p.default_size, quality=body.quality or p.default_quality,
        n=body.n or 1, extra=body.extra,
        assets=[{"library": a.library, "group_id": r.group_id,
                 "group_name": r.group.name, "image_ids": a.image_ids}
                for a, r in _pair(body.assets, rows)])
    db.add(t); db.commit(); db.refresh(t)
    task_runner.submit(t.id)
    return {"id": t.id, "status": t.status}
```
（`TaskIn` 按规格 §5.4：prompt_name/prompt_content/provider_id 必填，n∈[1,10] 且不超过该源站 param_options.n_max；`_pair` 把 assets 与首个展开图关联——实现时按顺序 zip。列表/详情/rerun/delete 按规格补齐：rerun 复制快照新建并 submit；delete 只删记录保留磁盘文件。）

`app/main.py` 启动钩子：
```python
    from .services import task_runner
    from .database import SessionLocal
    from .config import settings
    task_runner.init_runner(SessionLocal, settings.MAX_CONCURRENT_TASKS)
    # 重置遗留任务
    s = SessionLocal()
    s.query(GenTask).filter(GenTask.status.in_(("pending", "running"))).update(
        {"status": "failed", "error_message": "服务重启，任务中断"}, synchronize_session=False)
    s.commit(); s.close()
```

- [ ] **步骤 4：运行验证通过**

运行：`python -m pytest tests/test_task_flow.py -v`
预期：3 passed（Mock 全流程 ≤15s）

- [ ] **步骤 5：Commit**

```bash
git add app/ tests/
git commit -m "feat(backend): 生图任务 API、线程池后台执行与 Mock 端到端"
```

---

### 任务 9：全部路由装配 + /files 静态 + 冒烟

**文件：** 修改 `app/main.py`、`tests/test_main_smoke.py`（新建）

- [ ] **步骤 1：编写失败的测试**

`tests/test_main_smoke.py`：
```python
def test_full_app_boots_and_serves():
    from app.main import app
    from httpx import Client, ASGITransport
    c = Client(ASGITransport(app=app), base_url="http://t")
    assert c.get("/api/prompts").status_code == 200
    assert c.get("/api/libraries/face/groups").status_code == 200
    assert c.get("/api/providers").status_code == 200
    assert c.get("/api/tasks").status_code == 200
    assert c.get("/api/docs").status_code == 200      # Swagger 可用
```

- [ ] **步骤 2：运行验证失败**

运行：`python -m pytest tests/test_main_smoke.py -v`
预期：main 装配不全导致 FAIL

- [ ] **步骤 3：实现**

main.py 完整装配：四个路由 + `/files/libraries` 与 `/files/outputs` 静态挂载 + 任务启动重置 + runner 初始化。任务相关的 conftest client 在本任务后可直接改用 `app.main.app`。

- [ ] **步骤 4：运行验证通过**

运行：`python -m pytest tests/ -v`
预期：全绿（此前全部测试不回归）

- [ ] **步骤 5：Commit**

```bash
git add app/ tests/
git commit -m "feat(backend): 全路由装配、静态挂载与冒烟测试"
```

---

### 任务 10：启动入口 + 手工验收

**文件：** 创建 `run.py`、`README.md`

- [ ] **步骤 1：实现 run.py**

```python
import uvicorn
from app.config import settings

if __name__ == "__main__":
    from app.main import app
    print(f"生图工作台后端: http://127.0.0.1:{settings.APP_PORT}/api/docs")
    uvicorn.run(app, host="127.0.0.1", port=settings.APP_PORT, log_level="info")
```

- [ ] **步骤 2：手工验收（Mock，零额度）**

1. `python run.py` 启动无报错；
2. 打开 `/api/docs`，用 Swagger 建 Mock 源站 → 建组上传图 → POST /api/tasks；
3. 轮询任务至 success，确认 `outputs/<prompt名>/<时间戳_id>/` 下有图与 task.json；
4. 确认 tests 全绿：`python -m pytest tests/ -v`。

- [ ] **步骤 3：Commit**

```bash
git add run.py README.md
git commit -m "feat(backend): 启动入口与验收文档"
```

---

## 自检记录

- 规格覆盖：§3 配置（任务 1）、§4 六表（任务 2）、§5.1（任务 3）、§5.2（任务 4/5）、§5.3（任务 6）、§5.4+§6（任务 7/8）、§2.1 main 装配（任务 9/10）；§7 起前端计划另行覆盖。
- 占位符扫描：Provider/GenTask 模型标注"按规格全字段写全"并给出列清单——实现者以规格 §4 DDL 为唯一权威，无悬空引用。
- 类型一致性：`ensure_database`/`get_db`/`storage.DATA_DIR`/`generator.OUTPUT_DIR`/`task_runner.init_runner` 命名在各任务间一致。
