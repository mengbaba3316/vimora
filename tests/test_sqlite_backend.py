"""SQLite 本地存储后端测试（exe 分发形态的存储层）。"""
import os

from sqlalchemy.orm import sessionmaker


def test_sqlite_backend(tmp_path):
    monkey_db = tmp_path / "data"
    os.environ["DB_BACKEND"] = "sqlite"
    try:
        from app.config import Settings
        s = Settings()
        s.DATA_DIR = str(monkey_db)
        s.OUTPUT_DIR = str(tmp_path / "outputs")
        assert s.is_sqlite

        from app import database, models
        engine = database.ensure_database(s)

        Session = sessionmaker(bind=engine)
        db = Session()
        # 种子库自动灌入
        libs = db.query(models.Library).order_by(models.Library.sort_order).all()
        assert [l.key for l in libs] == ["face", "outfit", "socks", "pose"]
        # BigInteger 主键在 SQLite 上自增（_PK 方言变体）
        db.add_all([models.Provider(name="甲"), models.Provider(name="乙")])
        db.commit()
        ids = sorted(p.id for p in db.query(models.Provider).all())
        assert ids[0] > 0 and ids[1] == ids[0] + 1
        # 单文件库落在 DATA_DIR
        assert os.path.exists(os.path.join(str(monkey_db), "platform.db"))
        db.close()
    finally:
        os.environ.pop("DB_BACKEND", None)
