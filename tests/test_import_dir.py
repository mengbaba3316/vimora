from .test_storage_libraries_api import png_bytes

def test_import_dir(client, tmp_path):
    src = tmp_path / "袜子库"
    (src / "条纹袜").mkdir(parents=True)
    (src / "纯色袜" / "子目录").mkdir(parents=True)          # 递归导入验证
    (src / "条纹袜" / "a.png").write_bytes(png_bytes())
    (src / "纯色袜" / "子目录" / "b.png").write_bytes(png_bytes())
    (src / "根散图.png").write_bytes(png_bytes())
    (src / "坏文件.gif").write_bytes(b"GIF89a")
    r = client.post("/api/libraries/socks/import-dir", json={"source_dir": str(src)})
    j = r.json()
    assert r.status_code == 200
    assert j["groups_created"] == 3 and j["images_imported"] == 3 and j["skipped"] == 1
    names = {g["name"] for g in client.get("/api/libraries/socks/groups").json()}
    assert {"条纹袜", "纯色袜", "未分组"} <= names
    again = client.post("/api/libraries/socks/import-dir", json={"source_dir": str(src)}).json()
    assert again["groups_merged"] == 3 and again["groups_created"] == 0

def test_import_dir_not_exists(client, tmp_path):
    r = client.post("/api/libraries/socks/import-dir", json={"source_dir": str(tmp_path / "无")})
    assert r.status_code == 400
