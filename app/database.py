import pymysql
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

class Base(DeclarativeBase): pass

def ensure_database(s=settings):
    """按 DB_BACKEND 初始化存储并返回 engine：sqlite = 单文件本地库；mysql = 现行为不变。"""
    if s.is_sqlite:
        return _ensure_sqlite(s)
    return _ensure_mysql(s)

def _ensure_sqlite(s):
    """SQLite 本地库：单文件落在 DATA_DIR/platform.db，WAL + 线程安全 + 建表 + 种子。"""
    engine = create_engine(s.db_url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _sqlite_pragma(dbapi_conn, _):   # 后台线程并发写必须 WAL + busy_timeout
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()

    Base.metadata.create_all(engine)   # 新库直接建当前 schema，无需 MySQL 的补列/枚举迁移
    _seed_libraries(engine)
    print(f"[存储] SQLite 本地库：{s.db_url.replace('sqlite:///', '')}")
    return engine

def _ensure_mysql(s=settings):
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
    _migrate_libraries(engine)
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

# 素材库种子（key 与旧枚举值一致，color 用主题 token，前端深浅色主题自动适配）
_LIBRARY_SEED = [
    ("face", "人脸", "var(--lib-face)", 1),
    ("outfit", "服装", "var(--lib-outfit)", 2),
    ("socks", "袜子", "var(--lib-socks)", 3),
    ("pose", "姿势", "var(--lib-pose)", 4),
]

def _seed_libraries(engine):
    """library 表为空则灌入四类种子（跨方言：MySQL/SQLite 通用，幂等）。"""
    with engine.begin() as conn:
        has_rows = conn.execute(text("SELECT 1 FROM `library` LIMIT 1")).fetchone()
        if has_rows:
            return
        for key, name, color, sort in _LIBRARY_SEED:
            conn.execute(text(
                "INSERT INTO `library` (`key`, name, color, sort_order, enabled) "
                "VALUES (:k, :n, :c, :s, 1)"),
                {"k": key, "n": name, "c": color, "s": sort})

def _migrate_libraries(engine):
    """素材库可配置化迁移（幂等，MySQL 专用）：
    1. library 表为空 → 灌入四类种子数据；
    2. asset_group/asset_image 的 library 列若仍是旧枚举 → 按 key 映射转 BIGINT id，
       磁盘目录名用 key（file_path 不变），存量素材零迁移。
    """
    _seed_libraries(engine)
    with engine.connect() as conn:
        for table in ("asset_group", "asset_image"):
            dtype = conn.exec_driver_sql(
                "SELECT DATA_TYPE FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s "
                "AND COLUMN_NAME = 'library'", (table,)).scalar()
            # 上次中断可能留下半成品 library_new 列：先清掉再按完整流程重走
            leftover = conn.exec_driver_sql(
                "SELECT 1 FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s "
                "AND COLUMN_NAME = 'library_new'", (table,)).fetchone()
            if dtype != "enum":
                if leftover:
                    conn.exec_driver_sql(f"ALTER TABLE `{table}` DROP COLUMN library_new")
                    conn.commit()
                continue
            if not leftover:
                conn.exec_driver_sql(f"ALTER TABLE `{table}` ADD COLUMN library_new BIGINT NULL")
            # 旧枚举列与新建 library 表排序规则可能不同（unicode_ci vs 0900_ai_ci），
            # JOIN 显式统一到 unicode_ci（建库默认），否则 1267 混排规则错误
            conn.exec_driver_sql(
                f"UPDATE `{table}` g JOIN `library` l "
                f"ON l.`key` COLLATE utf8mb4_unicode_ci = g.library "
                f"SET g.library_new = l.id")
            conn.exec_driver_sql(f"ALTER TABLE `{table}` DROP COLUMN library")
            conn.exec_driver_sql(
                f"ALTER TABLE `{table}` CHANGE COLUMN library_new library BIGINT NOT NULL")
            if table == "asset_group":   # 删列时旧唯一索引随之删除，换列后重建
                conn.exec_driver_sql(
                    "ALTER TABLE asset_group ADD UNIQUE KEY uk_group_library_name (library, name)")
            conn.commit()
        # MySQL 删枚举列可能把 (library, name) 复合索引收窄成 (name)（上次转换中断也会
        # 留下错误索引）：校正为 (library, name)，恢复「库内组名唯一」语义。幂等。
        cols = [r[0] for r in conn.exec_driver_sql(
            "SELECT COLUMN_NAME FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'asset_group' "
            "AND INDEX_NAME = 'uk_group_library_name'").fetchall()]
        if cols and sorted(cols) != ["library", "name"]:
            conn.exec_driver_sql("ALTER TABLE asset_group DROP INDEX uk_group_library_name")
            conn.exec_driver_sql(
                "ALTER TABLE asset_group ADD UNIQUE KEY uk_group_library_name (library, name)")
            conn.commit()
        elif not cols:
            conn.exec_driver_sql(
                "ALTER TABLE asset_group ADD UNIQUE KEY uk_group_library_name (library, name)")
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
