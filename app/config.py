import os
import sys
from dotenv import load_dotenv
load_dotenv()


def _base_dir() -> str:
    """应用根目录：开发态 = 当前工作目录；PyInstaller 冻结态 = exe 所在目录
    （双击启动时 cwd 即 exe 目录，但被其他程序带 cwd 启动时也稳）。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.getcwd()


class Settings:
    def __init__(self):
        # 存储后端：mysql（默认，现行为不变）| sqlite（单文件本地库，随 exe 分发）
        self.DB_BACKEND = os.getenv("DB_BACKEND", "mysql").strip().lower()
        self.DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
        self.DB_PORT = int(os.getenv("DB_PORT", "3306"))
        self.DB_USER = os.getenv("DB_USER", "root")
        self.DB_PASSWORD = os.getenv("DB_PASSWORD", "")
        self.DB_NAME = os.getenv("DB_NAME", "image_gen_platform")
        self.TEST_DB_NAME = os.getenv("TEST_DB_NAME", "image_gen_platform_test")
        base = _base_dir()
        self.DATA_DIR = os.getenv("DATA_DIR", os.path.join(base, "data"))
        self.OUTPUT_DIR = os.getenv("OUTPUT_DIR", os.path.join(base, "outputs"))
        # 语义：单个源站的并发上限（每站各自独立计数），不是全局总数
        self.MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "2"))
        self.APP_PORT = int(os.getenv("APP_PORT", "8765"))

    @property
    def db_url(self):
        if self.DB_BACKEND == "sqlite":
            # 单文件库落在 DATA_DIR，随数据目录一起备份/迁移
            os.makedirs(self.DATA_DIR, exist_ok=True)
            return "sqlite:///" + os.path.join(self.DATA_DIR, "platform.db").replace("\\", "/")
        return (f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4")

    @property
    def is_sqlite(self):
        return self.DB_BACKEND == "sqlite"


settings = Settings()
