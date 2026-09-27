"""异步源站适配器：提交拿 task_id → 轮询查询路径 → 适配成同步响应结构。

约定（中转站公开文档规范，如噜皮 image.mlgb7.com）：
- 提交：gen/edits 请求体注入 async=true，返回 HTTP 202 + task_id（兜底 id 字段）；
- 查询：GET {task_query_path}?ids={task_id} → items[0].{status, terminal, results[]}；
- results[] 元素与 OpenAI images 响应的 data[] 同构（url / b64_json），
  轮询到终态后包成 {"data": [...]} 交回 task_runner，落盘复用 save_results。

仅按上述字段解析，不绑定具体站点；站点差异若超出约定，再扩展此处。
"""
import time
from typing import Tuple

import requests

POLL_HTTP_TIMEOUT = 30    # 单次轮询的 HTTP 超时（秒）
SUBMIT_HTTP_TIMEOUT = 120  # 提交应秒回 202；站点若不识别 async 会走同步，别干等总超时

TERMINAL_STATUSES = {"success", "succeeded", "completed", "failed", "cancelled", "canceled"}


def submit(p, url: str, kwargs: dict) -> str:
    """注入 async=true 提交，返回中转站 task_id。失败抛 RuntimeError。"""
    if "json" in kwargs:                          # generations：JSON 体
        kwargs["json"] = {**kwargs["json"], "async": True}
    else:                                          # edits：multipart 表单体
        kwargs["data"] = {**kwargs.get("data", {}), "async": "true"}
    kwargs["timeout"] = min(p.timeout_seconds, SUBMIT_HTTP_TIMEOUT)
    try:
        resp = requests.post(url, **kwargs)
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"异步提交请求失败：{e}") from e
    if resp.status_code != 202:
        raise RuntimeError(f"异步提交未返回 202（实际 HTTP {resp.status_code}，"
                           f"该站可能不支持 async 参数）\n{resp.text[:2000]}")
    try:
        body = resp.json()
    except ValueError:
        raise RuntimeError(f"异步提交 202 但响应不是 JSON：{resp.text[:500]}")
    task_id = body.get("task_id") or body.get("id")
    if not task_id:
        raise RuntimeError(f"异步提交 202 但未返回 task_id：{resp.text[:500]}")
    return str(task_id)


def poll_until_terminal(p, task_id: str) -> Tuple[dict, dict]:
    """轮询到终态，返回 (同构响应 {"data": [...]}, 终态 item)。

    超过 timeout_seconds 总预算仍未终态 → RuntimeError（提示凭 task_id 追回）。
    """
    interval = max(1, p.poll_interval_seconds or 10)
    deadline = time.time() + max(30, p.timeout_seconds)
    last_text = ""
    while time.time() < deadline:
        time.sleep(interval)
        try:
            r = requests.get(f"{p.base_url.rstrip('/')}{p.task_query_path}",
                             params={"ids": task_id},
                             headers={"Authorization": f"Bearer {p.api_key}"},
                             timeout=(10, POLL_HTTP_TIMEOUT))
            last_text = r.text
        except requests.exceptions.RequestException:
            continue   # 单次轮询网络抖动不连坐，吃满预算为止
        if r.status_code != 200:
            continue
        try:
            items = r.json().get("items", [])
        except ValueError:
            continue
        item = items[0] if items else None
        if not item:
            continue
        if item.get("terminal") or item.get("status") in TERMINAL_STATUSES:
            return _extract(item, task_id), item
    raise RuntimeError(
        f"异步轮询超时：{p.timeout_seconds} 秒内未到终态。中转站可能仍会出图并扣费，"
        f"可凭 task_id={task_id} 到其后台或查询接口追取；"
        f"最近一次查询响应：{last_text[:500]}")


def _extract(item: dict, task_id: str) -> dict:
    """终态 item → 与同步响应同构的 {"data": [...]}。"""
    status = item.get("status")
    results = item.get("results") or []
    if status not in ("success", "succeeded", "completed"):
        err = item.get("public_error") or item.get("error_code") or f"status={status}"
        raise RuntimeError(f"中转站异步任务失败（task_id={task_id}）：{str(err)[:500]}")
    if not results:
        raise RuntimeError(f"中转站异步任务成功但未返回图片（task_id={task_id}）")
    return {"data": results}
