# AI 生图工作台（后端）

单人使用的本地生图工作台后端：提示词 + 四类参考图（人脸/服装/袜子/姿势）组合，经 OpenAI 兼容中转站出图，产出按提示词归档。FastAPI + SQLAlchemy 2.0 + MySQL 8，内置本地 Mock 源站可零额度跑通全流程。

## 环境要求

- Python 3.9+
- MySQL 8.x（本机或可达远程）
- 依赖安装：`pip install -r requirements.txt`

## 配置

复制 `.env.example` 为 `.env` 按需修改（环境变量亦可，`.env` 不覆盖已存在的环境变量）：

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `DB_HOST` / `DB_PORT` | `127.0.0.1` / `3306` | MySQL 地址 |
| `DB_USER` / `DB_PASSWORD` | `root` / 空 | 数据库账号（需建库权限，或按下方提示手工建库） |
| `DB_NAME` | `image_gen_platform` | 业务库 |
| `TEST_DB_NAME` | `image_gen_platform_test` | 测试库（pytest 用，自动建删） |
| `DATA_DIR` | `data` | 素材库落盘根目录（`data/libraries/<库>/…`） |
| `OUTPUT_DIR` | `outputs` | 生图结果落盘根目录 |
| `MAX_CONCURRENT_TASKS` | `2` | 后台生图线程数 |
| `APP_PORT` | `8765` | 服务端口 |

启动时自动建库建表（`CREATE DATABASE IF NOT EXISTS … DEFAULT CHARSET utf8mb4`）。连接失败会打印中文诊断；若账号无建库权限，请先手工执行：

```sql
CREATE DATABASE image_gen_platform DEFAULT CHARSET utf8mb4;
```

## 启动

```bash
python run.py
```

- Swagger 文档：`http://127.0.0.1:8765/api/docs`
- 所有 REST 路由挂在 `/api` 前缀下；素材与结果图经 `/files/libraries`、`/files/outputs` 静态暴露。
- 服务重启时遗留的 pending/running 任务自动置为 failed（任务不跨进程存活）。

## API 一览

| 分组 | 路由 | 说明 |
| --- | --- | --- |
| 提示词 | `GET/POST /api/prompts`、`GET/PUT/DELETE /api/prompts/{id}` | CRUD + 关键词/标签搜索 |
| 素材库 | `GET/POST /api/libraries/{lib}/groups`、`PUT/DELETE …/groups/{id}` | 四库（face/outfit/socks/pose）分组 |
| | `GET/POST /api/libraries/{lib}/images`、`PUT/DELETE …/images/{id}` | 上传/移动/删除图片（落盘 `DATA_DIR`） |
| | `POST /api/libraries/{lib}/import-dir` | 按磁盘路径批量导入（一级子目录=组，递归） |
| 源站 | `GET/POST /api/providers`、`GET/PUT/DELETE /api/providers/{id}` | 中转站 CRUD（type: openai/mock；空 api_key 更新保留原值） |
| | `POST /api/providers/{id}/test` | 连通性测试（GET `/v1/models`，mock 不出网） |
| 任务 | `POST /api/tasks` | 建任务并提交后台执行，返回 **202**；有 assets 走 edits，无则 generations |
| | `GET /api/tasks`、`GET /api/tasks/{id}` | 列表（状态/关键词/prompt 过滤分页）与详情轮询 |
| | `POST /api/tasks/{id}/rerun` | 按快照复制重跑 |
| | `DELETE /api/tasks/{id}` | 只删记录，磁盘成果保留 |

`POST /api/tasks` 请求体中无值字段可传显式 `null`（如 `assets: null` → 自动按 generations 处理）；源站返回非 200 时任务置 failed，`error_message` 含状态码与响应体前 2000 字。

## Mock 全流程验收（零额度）

1. `python run.py` 启动，打开 `/api/docs`；
2. `POST /api/providers`：`{"name": "Mock", "type": "mock"}`；
3. `POST /api/libraries/face/groups` 建组，`POST /api/libraries/face/images` 上传图片；
4. `POST /api/tasks`（provider 指向 Mock，可带 assets）→ 轮询 `GET /api/tasks/{id}` 至 `success`；
5. 确认 `outputs/<提示词名>/<时间戳_任务id>/` 下有结果图与 `task.json`（任务全字段快照，含 finished_at/error_message），图片可经返回的 `/files/outputs/...` URL 直接访问。

## 测试

```bash
python -m pytest tests/ -v
```

测试使用 `TEST_DB_NAME` 指定的测试库，落盘指到临时目录，不污染真实 `data/`、`outputs/`。

## 目录结构

```
app/
├── config.py            # .env / 环境变量配置
├── database.py          # 建库建表、engine/会话
├── models.py            # 六表 ORM（prompt/asset_group/asset_image/provider/gen_task/task_image）
├── schemas.py           # 请求体校验
├── main.py              # 应用装配（路由、静态目录、执行器、遗留任务清理）
├── routers/             # prompts / libraries / providers / tasks
├── services/            # storage（素材落盘）/ generator（请求拼接与结果落盘）/ task_runner（线程池执行）/ mock_provider
└── utils/               # 文件名安全化、图片读写
```
