import os

DATA_DIR = "data"   # main 启动时与测试中由 settings 覆盖
ALLOWED = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
MAX_SIZE = 20 * 1024 * 1024


def lib_dir(library: str) -> str:
    d = os.path.join(DATA_DIR, "libraries", library)
    os.makedirs(d, exist_ok=True); return d


def save_image(library: str, group_id: int, filename: str, data: bytes) -> str:
    """落盘并返回相对 DATA_DIR/libraries 的 POSIX 路径。校验放路由层。"""
    from ..utils.filenames import uuid_filename
    d = os.path.join(lib_dir(library), str(group_id))
    os.makedirs(d, exist_ok=True)
    name = uuid_filename(filename)
    with open(os.path.join(d, name), "wb") as f: f.write(data)
    return f"{library}/{group_id}/{name}"


def delete_image(rel_path: str):
    p = os.path.join(DATA_DIR, "libraries", rel_path)
    if os.path.exists(p): os.remove(p)
