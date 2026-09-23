# image_gen_platform 集成收尾报告

- 日期：2026-09-23
- 执行：集成收尾代理（main 分支主检出 `E:\PythonProjects\image_gen_platform`）
- 基线：`9440db8`（feature/frontend 合并完成，35 passed）
- 结果：**DONE**

## 一、提交记录（每项独立 commit）

| Commit | 内容 |
|---|---|
| `ca47e22` | feat(backend): 托管前端 SPA（frontend/dist 存在时挂载根路径） |
| `9c51004` | fix(frontend): 历史任务五态展示由后端四态派生（审查裁定项） |

工作树终态：干净（仅会话开始前就存在的 `__pycache__/` 未跟踪目录；data/、outputs/、frontend/dist、node_modules、.superpowers/ 均在 .gitignore 内）。

## 二、任务 1：后端托管 SPA（ca47e22）

`app/main.py` 的 `create_app()` 在全部 `/api` 路由（include_router ×4）与 `/files/libraries`、`/files/outputs` 两个挂载**之后**追加：

```python
dist = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "frontend", "dist")
if os.path.isdir(dist):
    app.mount("/", StaticFiles(directory=dist, html=True), name="spa")
```

- `os` 与 `StaticFiles` 顶部既有导入，未重复 import；`abspath` 为健壮性加固（语义与给定片段一致）。
- 挂载顺序核实：`Mount("/")` 最后注册，Starlette 按注册顺序匹配，完整匹配优先，故不遮蔽 `/api/*`、`/files/*`、`/api/docs`。
- dist 缺失时跳过挂载（纯后端模式不受影响）。
- **接线核实（任务 9 既有，已确认存在）**：`create_app` 中 `storage.DATA_DIR = settings.DATA_DIR`（main.py:20）、`generator.DATA_DIR = settings.DATA_DIR`（main.py:21）、`generator.OUTPUT_DIR = settings.OUTPUT_DIR`（main.py:22）。

## 三、任务 2：前端状态派生（9c51004）

`frontend/src/views/HistoryView.vue`（后端 status 权威四值：pending/running/success/failed，规格 §4 DDL）：

1. **normStatus 派生**（签名由 `(s)` 改为 `(t)`）：
   - `pending → 'queued'`；
   - `status==='success' && (t.ok ?? okCount(t)) < t.n → 'partial'`；
   - 其余原值。
   - 说明：裁定项公式为 `(t.ok ?? 0)`，但后端 `to_dict` 并无 `ok` 字段，若字面实现则所有 success 都会误判为 partial。故按「成功张数」语义实现为 `t.ok ?? okCount(t)`（okCount = images 数，列表/详情接口均含 images）：后端将来若提供 `ok` 字段则自动优先生效，当前用 images 数兜底。代码内已注释。
2. **行级 chip、详情抽屉 warnbox、结果区提示（resHint/resSnapshot）全部改用派生值**（`stMeta(t)`、`normStatus(detail)`）。
3. **筛选映射**（refresh()）：
   - 「排队中」→ 请求 `status=pending`；
   - 「部分成功」→ 请求 `status=success` 后客户端按 `ok<n` 过滤；total 同步取过滤后条数（后端 total 是 success 总数，含全部成功会虚高）；
   - 其余直传。
4. **主题纪律**：未新增任何裸色值，全部沿用既有 `var(--*)` token。
5. 派生逻辑经 Node 7/7 用例验证（pending→queued；success 全量→success；success 部分→partial；`ok` 字段优先；failed/running 原值）。

## 四、任务 3：构建 + Mock 全流程验收（零真实额度）

### 3.1 构建
- `npm ci`（node v22.21.0，85 packages）+ `npm run build`（vite 8.3.0）：**成功**，产物 `frontend/dist/`（index.html + assets，JS 1.12MB / CSS 385KB，仅有 chunk>500kB 的体积提示，非错误）。

### 3.2 成功路径（服务 `python run.py`，PID 42900，端口 8765）

| # | 步骤 | 结果 |
|---|---|---|
| 1 | POST /api/providers（type=mock，name=集成验收Mock） | 200，id=2 |
| 2 | POST /api/libraries/face/groups（集成验收组） | 200，id=2 |
| 3 | Pillow 现造 256×256 PNG → POST /api/libraries/face/images 上传 1 张 | `{"imported":1,"skipped":0,"errors":[]}` |
| 4 | POST /api/prompts | 200，id=1 |
| 5 | POST /api/tasks（assets=[{library:face,image_ids:[2]}] 与显式 null 的 prompt_id/model/size/quality/extra 混合，n=2） | **202** `{"id":2,"status":"pending"}` |
| 6 | 轮询 GET /api/tasks/2 | → running → **success** |
| 7 | images 断言 | 2/2 张，均含 `url=/files/outputs/...`（与 n 一致） |
| 8 | 磁盘断言 | `outputs/集成验收任务/20260923214139_2/` 存在 2 张 PNG（7847B ×2）+ task.json（status=success、files×2、elapsed≈2.05s） |
| 9 | GET /（根路径） | **200**，`text/html`，返回 SPA index.html（`<title>生图工作台</title>`） |
| 10 | GET /files/outputs/…（URL 编码中文路径） | **200**，`image/png`，7847 字节与磁盘一致 |
| 11 | GET /files/libraries/…（上传的参考图） | 200 |

注：步骤 10 首次用未编码中文路径 curl 得 404，属 curl 未做百分号编码，URL 编码后 200（浏览器行为等同编码后）。

### 3.3 失败路径
- POST /api/providers（type=openai，base_url=http://127.0.0.1:1，无真实 Key）→ id=3；
- POST /api/tasks（assets:null + 显式 null 混合）→ **202** id=3 → 轮询至 **failed**；
- error_message 含完整连接错误：`HTTPConnectionPool(host='127.0.0.1', port=1): Max retries exceeded ... [WinError 10061] 由于目标计算机积极拒绝，无法连接。`（符合规格 §8 不抛请求层异常、落任务失败并留诊断的要求）。

### 3.4 筛选映射实测（对前端 refresh 的请求口径）
- `status=pending`（「排队中」映射）→ 0 条（任务均已终态，符合预期）；
- `status=success`（「部分成功」的数据源）→ 返回 2 条 success，客户端 `ok<n` 过滤后 0 条 partial（两条均满额成功，派生=success，正确）；
- `status=failed` → 1 条（失败任务）。

### 3.5 回归
- `python -m pytest tests/ -q` → **35 passed**（在 dist 已构建、SPA 挂载已生效的状态下运行，无回归）。

### 3.6 清理
- DB（经 API DELETE，同时回归验证了删除接口）：我的源站 2/3、提示词 1、组 2（含上传图，磁盘文件随删）、任务 2/3；另清除上次中断验收遗留：源站 1（Mock验收源站）、组 1（验收组A）、任务 1（快照）。终态校验：providers=[]、prompts 空、tasks total=0、groups=[]。
- 磁盘：`outputs/` 内全部产物（集成验收任务、快照×2）删除，保留空目录本身；`data/` 下 0 文件，目录保留；`frontend/dist`、`node_modules` 保留（构建产物）。
- 临时载荷：`.superpowers/tmp/`（UTF-8 JSON 载荷与测试 PNG）已删除。注：中文 JSON 体经 shell 内联 `curl -d` 会被 Windows 控制台编码破坏（首验报 body parsing 错误），故载荷落盘 UTF-8 文件后用 `curl --data-binary @file`。
- 进程：`taskkill /PID 42900 /T /F` 杀树成功，端口 8765 已确认关闭。

## 五、发现与疑虑

1. **【重要】测试套件存在产物泄漏（pre-existing，非本次改动引入）**：`tests/test_task_flow.py::test_rerun_copies_snapshot_and_delete_keeps_disk`（第 106-124 行）对 rerun 新任务不等待终态即结束；worker 线程在 fixture 拆卸（monkeypatch 还原 `generator.OUTPUT_DIR` 为真实 `outputs/`）之后才执行落盘，把「快照」任务产物写进真实 `outputs/快照/`（本次 21:44 与上次会话 21:32 的遗留产物均由此产生；task.json 内 provider_name="Mock"、prompt_content="y" 与该测试数据完全吻合）。建议后续修复：测试内等待 rerun 任务至终态，或在 client fixture 拆卸时 `executor.shutdown(wait=True)`。本次仅记录并清理产物，未越权改动测试语义。
2. **SPA 深链接 404**：`html=True` 的 StaticFiles 对 `/history` 等前端路由深链接/刷新返回 404 JSON（GET / 正常）。验收范围仅要求 GET /，故按裁定代码实现未加 catch-all 回退；如需支持深链接，后续可将未知 GET 回退到 index.html。
3. **未知 /api/* 路径行为未变**：实测 `/api/nonexistent` 仍返回 404 JSON（StaticFiles html=True 找不到 404.html 时走 FastAPI 的 JSON 404 处理器），现有测试不受影响（35 passed 佐证）。
4. **partial 端到端不可构造**：mock 源站恒返回 n 张全成功图，无法以真实请求造出「部分成功」；partial 派生已用 Node 单测（7/7）与代码评审覆盖，建议后续为 mock_provider 增加可控少图模式以便端到端验证。
5. 前端构建体积提示（JS chunk >500kB）：非错误，Element Plus 全量引入所致，与本次收尾无关，不处理。

## 六、结论

三项任务全部完成：SPA 托管（ca47e22）、五态派生（9c51004）、构建 + 零额度 Mock 全流程验收（成功路径、失败路径、静态文件、全量回归 35 passed）全部通过；验收产物（磁盘 + DB）已清理，服务进程已按 PID 杀树关闭。平台处于可交付状态，遗留疑虑见第五节。

## 七、收尾追补（2026-09-23 第二轮）

针对第五节疑虑 1、2 的两项收尾修复，各自独立 commit：

### 7.1 `1d145fb` fix(backend): rerun 测试等待终态，防验收产物泄漏

- `tests/test_task_flow.py::test_rerun_copies_snapshot_and_delete_keeps_disk`：rerun 后改为 `_wait_terminal`（15s 上限）轮询至终态并断言 success、images 张数与快照字段，测试体结束前 worker 必然已完成落盘；
- `app/services/task_runner.py` 新增 `shutdown(wait=True)`（等待在途/排队任务后置空 executor）；
- `tests/conftest.py` 的 client fixture teardown 由 `executor.shutdown(wait=False)` 改为 `task_runner.shutdown(wait=True)`：此刻 monkeypatch 未解除、表未 drop，残留 worker 的落盘仍指向 tmp_path，双保险覆盖未显式等待终态的用例（如 `test_task_success_flow` 末尾的 rerun）。
- 验证：`pytest tests/test_task_flow.py` 与全量 `pytest tests/` 各跑后 `outputs/` 均无「快照」残留（本轮调试期间出现的 `outputs/快照/20260923222409_2` 为修复前基线跑的残留，已清理）。

### 7.2 `79e4f79` feat(backend): SPA 深链接兜底（history 模式刷新返回 index.html）

- `app/main.py`：dist 存在时注册 catch-all `GET /{full_path:path}`（`include_in_schema=False`）：`api`/`files` 前缀请求维持 404；dist 内真实存在的文件（/assets/*、/favicon.svg）经 realpath 越界防护后按原文件 FileResponse 伺服；其余路径返回 `dist/index.html`。
- **实现偏离说明（必要）**：任务书要求 catch-all 注册在 SPA mount 之后，但实测 Starlette 按注册顺序取第一个完全匹配路由，`Mount("/")` 会吞掉所有 GET——catch-all 放其后永远不可达（隔离实验：`GET /history` 仍 404）。故兜底路由注册在 `Mount("/")` **之前**（仍在全部 /api、/files 路由之后），mount 保留为底层静态层，代码内已注释原因。
- 测试：`tests/test_main_smoke.py::test_spa_deeplink_refresh_serves_index_html`，断言 GET /history 200 且含 `<div id="app">`、GET / 200、/favicon.svg 按原文件伺服、未知 /api 路径仍 404；dist 未构建时 `skipif` 跳过。

### 7.3 回归与冒烟

- 全量 `python -m pytest tests/ -q` → **36 passed**（基线 35 + 新增 1，无回归）；
- `python run.py`（PID 47380，端口 8765）冒烟：GET / → 200 text/html；GET /history → 200 且含 `<div id="app">`；GET /api/prompts → 200 application/json；GET /favicon.svg → 200 image/svg+xml；GET /api/nope → 404。`taskkill /PID 47380 /T /F` 杀树成功，端口确认关闭；
- 工作树干净，`outputs/` 无测试残留。
