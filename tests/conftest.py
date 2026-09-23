import os, shutil
import pytest

# .env 的 DB_NAME 指向业务库，而测试必须落在测试库。app.config 导入时会执行
# load_dotenv()（默认不覆盖已存在的环境变量），所以必须在导入它之前强制设置。
os.environ["DB_NAME"] = "image_gen_platform_test"
os.environ["TEST_DB_NAME"] = "image_gen_platform_test"

from app.config import Settings

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
