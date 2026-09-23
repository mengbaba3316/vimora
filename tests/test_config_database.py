def test_settings_defaults(settings):
    assert settings.DB_NAME == "image_gen_platform_test"
    assert settings.MAX_CONCURRENT_TASKS >= 1

def test_ensure_database_creates_tables(test_engine):
    from sqlalchemy import inspect
    names = set(inspect(test_engine).get_table_names())
    assert {"prompt", "asset_group", "asset_image", "provider",
            "gen_task", "task_image"} <= names
