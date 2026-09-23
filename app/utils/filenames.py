import re, uuid
from datetime import datetime


def safe_dirname(name: str, maxlen: int = 80) -> str:
    name = re.sub(r'[\\/:*?"<>|\r\n]', "", name).strip().replace(" ", "_")
    return name[:maxlen] or "未命名"


def stamp(fmt: str = "%Y%m%d%H%M%S") -> str:
    return datetime.now().strftime(fmt)


def uuid_filename(original: str) -> str:
    return f"{uuid.uuid4().hex[:8]}_{original}"
