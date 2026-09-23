def test_settings_defaults(settings):
    assert settings.DB_NAME == "image_gen_platform_test"
    assert settings.MAX_CONCURRENT_TASKS >= 1

def test_ensure_database_creates_tables(test_engine):
    from sqlalchemy import inspect
    names = set(inspect(test_engine).get_table_names())
    assert {"prompt", "asset_group", "asset_image", "provider",
            "gen_task", "task_image"} <= names

def test_ensure_database_failure_prints_hint(capsys):
    """规格 §3：连接失败须打印中文提示（含手工建库 SQL 与配置检查指引）后再抛出。"""
    import pytest
    from app import database
    s = database.settings.__class__()     # 真实 Settings，读当前环境
    s.DB_PORT = 3399                      # 本机无服务的端口 → 连接被拒
    with pytest.raises(Exception):
        database.ensure_database(s)
    out = capsys.readouterr().out
    assert "无法连接 MySQL" in out
    assert f"CREATE DATABASE {s.DB_NAME} DEFAULT CHARSET utf8mb4;" in out
    assert "DB_HOST" in out and "DB_PASSWORD" in out
