import os, shutil
import pytest

# .env 的 DB_NAME 指向业务库，而测试必须落在测试库。app.config 导入时会执行
# load_dotenv()（默认不覆盖已存在的环境变量），所以必须在导入它之前强制设置。
os.environ["DB_NAME"] = "image_gen_platform_test"
os.environ["TEST_DB_NAME"] = "image_gen_platform_test"

from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app import models  # noqa: F401  导入即把六张表注册进 Base.metadata（否则 create_all 建不出表）

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

@pytest.fixture()
def client(test_engine, settings, monkeypatch):
    from fastapi import FastAPI
    from app.database import get_db
    from app.routers import prompts, libraries, library_types, providers, tasks
    from app.services import generator, storage, task_runner
    # 存储落盘指到 tmp_path，测试不污染真实 data/ 目录
    monkeypatch.setattr(storage, "DATA_DIR", settings.DATA_DIR)
    # 生图执行线程读素材与写结果同样指到 tmp_path
    monkeypatch.setattr(generator, "DATA_DIR", settings.DATA_DIR)
    monkeypatch.setattr(generator, "OUTPUT_DIR", settings.OUTPUT_DIR)
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    Session = sessionmaker(bind=test_engine, expire_on_commit=False)
    app = FastAPI()
    app.include_router(prompts.router, prefix="/api")
    app.include_router(libraries.router, prefix="/api")
    app.include_router(library_types.router, prefix="/api")
    app.include_router(providers.router, prefix="/api")
    app.include_router(tasks.router, prefix="/api")

    def override():
        s = Session()
        try:
            yield s
        finally:
            s.close()  # 与真实 get_db 一致；否则连接带事务滞留池中，drop_all 会死锁在元数据锁上
    app.dependency_overrides[get_db] = override
    # 后台执行线程用同一个 test_engine 的会话工厂（否则任务落在别库，轮询永远 pending）
    task_runner.init_runner(Session, settings.MAX_CONCURRENT_TASKS)
    # httpx>=0.28 的 ASGITransport 仅支持异步 Client，同步测试用 FastAPI 官方 TestClient
    from fastapi.testclient import TestClient
    c = TestClient(app)
    yield c
    c.close()
    # 等待在途/排队任务真正结束再 teardown：此刻 monkeypatch 未解除、表未 drop，
    # worker 的落盘仍指向 tmp_path；wait=False 会留下线程在 teardown 后写真实 outputs/
    task_runner.shutdown(wait=True)
