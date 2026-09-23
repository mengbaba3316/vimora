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
