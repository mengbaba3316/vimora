import base64
import io
import time
from typing import Optional, Tuple

from PIL import Image, ImageDraw


def generate(prompt: str, model: str, size: str, n: int, quality: str,
             extra: Optional[dict] = None) -> dict:
    """本地 Mock 源站：按 size 画一张带占位信息的 PNG，返回 OpenAI 风格 b64_json 响应。"""
    w, h = _parse_size(size)
    time.sleep(2)                                # 模拟真实源站耗时
    data = []
    for _ in range(n):
        img = Image.new("RGB", (w, h), (238, 240, 243))
        d = ImageDraw.Draw(img)
        d.rectangle([w // 8, h // 8, w * 7 // 8, h * 7 // 8], outline=(35, 39, 47), width=4)
        d.text((w // 10, h // 2 - 20), f"MOCK {model} {size} {quality}", fill=(35, 39, 47))
        d.text((w // 10, h // 2 + 20), prompt[:60], fill=(90, 100, 120))
        buf = io.BytesIO()
        img.save(buf, "PNG")
        data.append({"b64_json": base64.b64encode(buf.getvalue()).decode()})
    return {"created": int(time.time()), "data": data}


def _parse_size(size: str, default: Tuple[int, int] = (1024, 1024)) -> Tuple[int, int]:
    try:
        a, b = size.lower().split("x")
        return int(a), int(b)
    except Exception:
        return default
