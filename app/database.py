import pymysql
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

class Base(DeclarativeBase): pass

def ensure_database(s=settings):
    """库不存在则创建（utf8mb4），返回绑定该库的 engine。"""
    try:
        raw = pymysql.connect(host=s.DB_HOST, port=s.DB_PORT, user=s.DB_USER,
                              password=s.DB_PASSWORD)
    except Exception as e:
        # 规格 §3：连接失败给出中文诊断与手工建库 SQL（print 后 raise，保留原始堆栈）
        print(f"[启动失败] 无法连接 MySQL（{s.DB_USER}@{s.DB_HOST}:{s.DB_PORT}）：{e}\n"
              "请检查 .env / 环境变量中 DB_HOST、DB_PORT、DB_USER、DB_PASSWORD 配置是否正确、"
              "MySQL 服务是否已启动；若账号无建库权限，请先手工执行：\n"
              f"    CREATE DATABASE {s.DB_NAME} DEFAULT CHARSET utf8mb4;\n"
              "然后重新启动。")
        raise
    with raw.cursor() as c:
        c.execute(f"CREATE DATABASE IF NOT EXISTS `{s.DB_NAME}` "
                  "DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci")
    raw.commit(); raw.close()
    engine = create_engine(s.db_url, pool_pre_ping=True, pool_recycle=1800)
    Base.metadata.create_all(engine)
    _ensure_columns(engine)
    return engine

# create_all 只建缺表不补列：存量表的新增列在此自愈（幂等，缺才 ALTER）。
# (表, 列, DDL 片段) —— 新列默认值必须与 models.py 一致，存量行不受影响。
_MISSING_COLUMNS = [
    ("provider", "mode", "ENUM('sync','async') NOT NULL DEFAULT 'sync'"),
    ("provider", "task_query_path", "VARCHAR(200) NOT NULL DEFAULT ''"),
    ("provider", "poll_interval_seconds", "INT NOT NULL DEFAULT 10"),
    ("gen_task", "remote_task_id", "VARCHAR(200) NULL"),
]

def _ensure_columns(engine):
    with engine.connect() as conn:
        for table, col, ddl in _MISSING_COLUMNS:
            has = conn.exec_driver_sql(
                f"SELECT 1 FROM information_schema.COLUMNS "
                f"WHERE TABLE_SCHEMA = DATABASE() "
                f"AND TABLE_NAME = '{table}' AND COLUMN_NAME = '{col}'").fetchone()
            if not has:
                conn.exec_driver_sql(f"ALTER TABLE `{table}` ADD COLUMN `{col}` {ddl}")
        conn.commit()

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
