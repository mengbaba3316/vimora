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
        # 语义：单个源站的并发上限（每站各自独立计数），不是全局总数
        self.MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "2"))
        self.APP_PORT = int(os.getenv("APP_PORT", "8765"))

    @property
    def db_url(self):
        return (f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4")

settings = Settings()
