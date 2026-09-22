# AI 生图工作台（Image Generation Platform）设计规格

- 日期：2026-09-22
- 状态：待用户审查
- 性质：单人使用的本地工作台，核心是「提示词 + 四类参考图 → 中转站生图」的编排工具

---

## 1. 目标与非目标

### 1.1 目标

1. **提示词管理**：沉淀、检索、编辑 prompt（支持标签、关键字搜索）。
2. **四类参考图库**：人脸（face）、服装（outfit）、袜子（socks）、姿势（pose）。均为「组（款式/文件夹）→ 图片」两级结构，支持批量上传与**服务端按磁盘路径批量导入**（迁移存量档案）。
3. **API 源站管理**：维护多个 OpenAI 兼容中转站（名称、URL、Key、默认参数、路径覆盖）。
4. **生图工作台**：选 prompt → 编辑器内修改（仅本次任务生效）→ 编辑器内**局部查找/替换** → 四库自由多选参考图 → 选源站与参数 → 生成。
5. **任务历史**：结果图按「输出根目录 / prompt 名 / 时间戳任务文件夹 / 时间戳文件名」落盘，附带 `task.json` 参数快照，可回看、可一键重跑。
6. **Mock 源站**：内置不联网的模拟源站，用于开发验证与用户低成本的界面自测。

### 1.2 非目标（YAGNI）

- 不做用户系统、权限、多租户（localhost 单人使用，无鉴权）。
- 不做 prompt 版本管理。
- 不做在线图片编辑（裁剪/标注）。
- 不做额度/费用统计。
- 不对接非 OpenAI 兼容格式的 API（差异通过路径/字段覆盖尽量适配，不为某家写专用适配器）。

### 1.3 测试边界（重要）

- **开发者（AI）绝不使用真实 API Key 调用中转站**，一切端到端验证走 Mock 源站。
- 中转站的连通性、真实出图效果由用户自行配置后自测。
- 平台提供源站「连通性测试」按钮：仅请求 `{base_url}/v1/models`（免费接口，不消耗生图额度）。

---

## 2. 技术栈与总体架构

| 层 | 选型 | 说明 |
|---|---|---|
| 后端 | Python 3.11+ / FastAPI / uvicorn | REST API + 静态文件托管 + 后台任务线程池 |
| ORM | SQLAlchemy 2.0 + PyMySQL | 连接用户本地 MySQL 8 |
| 数据库 | MySQL（utf8mb4） | 只存元数据，图片不进库 |
| 前端 | Vue 3 + Vite + Element Plus + axios | SPA，构建产物由 FastAPI 托管 |
| HTTP 客户端 | requests | 调中转站（不用 OpenAI SDK） |
| 配置 | python-dotenv 读根目录 `.env` | MySQL 连接、目录、并发数 |

```
浏览器 (Vue3 SPA, http://127.0.0.1:8765)
   │  /api/**        REST
   │  /files/**      素材图与结果图静态访问
   ▼
FastAPI
   ├─ routers: prompts / libraries / providers / tasks
   ├─ services: storage(素材落盘) / task_runner(线程池) / generator(拼请求+落盘)
   ├─ MySQL (SQLAlchemy)
   └─ 磁盘: data/libraries/** 与 outputs/**
```

### 2.1 工程结构

```
image_gen_platform/
├── .env.example              # 用户复制为 .env 后填写
├── requirements.txt
├── run.py                    # 启动入口：建库建表、建目录、起 uvicorn
├── app/
│   ├── main.py               # FastAPI 工厂、路由挂载、/files 静态挂载
│   ├── config.py             # 读 .env
│   ├── database.py           # engine / SessionLocal / 建库建表
│   ├── models.py             # ORM 模型（对应第 4 节表）
│   ├── schemas.py            # Pydantic 请求/响应模型
│   ├── routers/
│   │   ├── prompts.py
│   │   ├── libraries.py
│   │   ├── providers.py
│   │   └── tasks.py
│   ├── services/
│   │   ├── storage.py        # 素材上传/导入/删除的文件操作
│   │   ├── task_runner.py    # ThreadPoolExecutor 调度
│   │   ├── generator.py      # edits/generations 拼接、响应落盘、状态机
│   │   └── mock_provider.py  # Mock 源站（Pillow 生成占位图）
│   └── utils/
│       ├── filenames.py      # 时间戳命名、目录名安全化
│       └── image_io.py       # b64_json 解码 / url 下载 → 文件
├── frontend/                 # Vue3 + Vite
│   ├── package.json
│   ├── vite.config.js        # dev 模式 /api、/files 代理到后端
│   ├── index.html
│   └── src/
│       ├── main.js
│       ├── App.vue           # 顶部导航：工作台/提示词/素材库/源站/历史
│       ├── api/index.js      # axios 封装
│       ├── components/
│       │   ├── PromptEditor.vue    # 含局部查找/替换工具条
│       │   └── AssetPicker.vue     # 四库通用的选择抽屉
│       └── views/
│           ├── Workbench.vue       # 生图工作台（首页）
│           ├── Prompts.vue
│           ├── Libraries.vue
│           ├── Providers.vue
│           └── History.vue
├── data/                     # 素材存储根（.env 可配 DATA_DIR）
│   └── libraries/face|outfit|socks|pose/<组id>/<uuid>.<ext>
├── outputs/                  # 输出根（.env 可配 OUTPUT_DIR）
└── tests/
    ├── conftest.py           # 测试库 image_gen_platform_test，自建自删
    ├── test_prompts_api.py
    ├── test_libraries_api.py
    ├── test_provider_adapter.py
    └── test_task_flow.py     # Mock 源站端到端
```

---

## 3. 配置（.env）

```ini
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=image_gen_platform

DATA_DIR=data                 # 素材存储根，相对项目根
OUTPUT_DIR=outputs            # 输出根，相对项目根
MAX_CONCURRENT_TASKS=2        # 生图并发线程数
APP_PORT=8765
```

启动流程（`python run.py`）：
1. 读 `.env`（无 `.env` 时以 `.env.example` 为模板报错提示）。
2. 连接 MySQL；若 `DB_NAME` 库不存在则 `CREATE DATABASE ... DEFAULT CHARSET utf8mb4`（无权限时给出手工建库 SQL 提示后退出）。
3. `Base.metadata.create_all` 建表（表已存在则跳过，不做自动迁移；字段变更阶段手动 `DROP` 重建或写一次性脚本）。
4. 创建 `DATA_DIR/libraries/`、`OUTPUT_DIR/` 目录。
5. 起 uvicorn（host 127.0.0.1，port `APP_PORT`）。

前端开发：`cd frontend && npm install && npm run dev`（Vite 代理 `/api`、`/files` 到 `127.0.0.1:APP_PORT`）。
部署：`npm run build` → FastAPI 将 `frontend/dist` 挂在 `/`，用户只需访问后端端口。

---

## 4. 数据库设计（MySQL DDL）

命名统一小写下划线；引擎 InnoDB；字符集 utf8mb4。 tags 用逗号分隔字符串（避免关联表，检索用 LIKE）。

```sql
-- 提示词库
CREATE TABLE prompt (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(100) NOT NULL,                 -- 名称，同时用作输出子目录名
  content     MEDIUMTEXT NOT NULL,                   -- 提示词正文
  tags        VARCHAR(255) NOT NULL DEFAULT '',      -- 逗号分隔
  remark      VARCHAR(500) NOT NULL DEFAULT '',
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_prompt_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 素材组（=款式/文件夹），四库共用一张表
CREATE TABLE asset_group (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  library     ENUM('face','outfit','socks','pose') NOT NULL,
  name        VARCHAR(100) NOT NULL,
  sort_order  INT NOT NULL DEFAULT 0,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_group_library_name (library, name),   -- 同库内组名唯一
  KEY idx_group_library (library, sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 素材图片
CREATE TABLE asset_image (
  id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  group_id      BIGINT NOT NULL,
  library       ENUM('face','outfit','socks','pose') NOT NULL,  -- 冗余，便于按库查
  original_name VARCHAR(255) NOT NULL,               -- 用户可改的展示名
  file_path     VARCHAR(500) NOT NULL,               -- 相对 DATA_DIR/libraries/ 的 POSIX 相对路径
  sort_order    INT NOT NULL DEFAULT 0,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_image_group (group_id, sort_order),
  CONSTRAINT fk_image_group FOREIGN KEY (group_id) REFERENCES asset_group(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- API 源站（中转站）
CREATE TABLE provider (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  name            VARCHAR(100) NOT NULL,
  type            ENUM('openai','mock') NOT NULL DEFAULT 'openai',
  base_url        VARCHAR(300) NOT NULL DEFAULT '',   -- 如 https://api.example.com（不带 /v1）
  api_key         VARCHAR(300) NOT NULL DEFAULT '',
  enabled         TINYINT(1) NOT NULL DEFAULT 1,      -- 停用后不出现在工作台可选列表
  gen_path        VARCHAR(200) NOT NULL DEFAULT '/v1/images/generations',
  edits_path      VARCHAR(200) NOT NULL DEFAULT '/v1/images/edits',
  image_field     VARCHAR(50)  NOT NULL DEFAULT 'image[]',  -- edits 多图字段名
  default_model   VARCHAR(100) NOT NULL DEFAULT 'gpt-image-1',
  default_size    VARCHAR(30)  NOT NULL DEFAULT '1024x1024',
  default_quality VARCHAR(30)  NOT NULL DEFAULT 'high',     -- 允许空串=不传该字段
  timeout_seconds INT NOT NULL DEFAULT 300,
  extra_params    JSON NULL,                          -- 附加表单/JSON 字段，随请求合并发送
  param_options   JSON NULL,                          -- 参数可选值方案（size/quality/resolution/n_max），NULL 用内置默认，见 5.3
  remark          VARCHAR(500) NOT NULL DEFAULT '',
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 生图任务（历史）
CREATE TABLE gen_task (
  id             BIGINT AUTO_INCREMENT PRIMARY KEY,
  prompt_id      BIGINT NULL,                         -- 来源提示词，可空；仅溯源用
  prompt_name    VARCHAR(100) NOT NULL,               -- 快照：输出子目录名
  prompt_content MEDIUMTEXT NOT NULL,                 -- 快照：实际发送的提示词
  provider_id    BIGINT NOT NULL,
  provider_name  VARCHAR(100) NOT NULL,               -- 快照
  endpoint       VARCHAR(20)  NOT NULL,               -- 'edits' | 'generations'
  model          VARCHAR(100) NOT NULL,
  size           VARCHAR(30)  NOT NULL,
  quality        VARCHAR(30)  NOT NULL DEFAULT '',
  n              INT NOT NULL DEFAULT 1,
  extra          JSON NULL,                           -- 附加参数快照（清晰度等非标准键），随请求合并发送
  assets         JSON NULL,                           -- 快照，结构见下
  status         ENUM('pending','running','success','failed') NOT NULL DEFAULT 'pending',
  error_message  TEXT NULL,                           -- 失败原因（截断 2000 字）
  output_dir     VARCHAR(500) NULL,                   -- 相对 OUTPUT_DIR，成功后有值
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  started_at     DATETIME NULL,
  finished_at    DATETIME NULL,
  KEY idx_task_status (status, created_at),
  KEY idx_task_prompt (prompt_name, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 任务结果图
CREATE TABLE task_image (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  task_id     BIGINT NOT NULL,
  file_path   VARCHAR(500) NOT NULL,                  -- 相对 OUTPUT_DIR
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_taskimage_task (task_id),
  CONSTRAINT fk_taskimage_task FOREIGN KEY (task_id) REFERENCES gen_task(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 4.1 `gen_task.assets` JSON 结构（快照）

```json
[
  { "library": "face",   "group_id": 3, "group_name": "模特A",   "image_ids": [11] },
  { "library": "outfit", "group_id": 7, "group_name": "白裙-夏季", "image_ids": [21, 22, 23] },
  { "library": "socks",  "group_id": 9, "group_name": "白袜-条纹", "image_ids": [41] },
  { "library": "pose",   "group_id": 2, "group_name": "站姿",     "image_ids": [55, 56] }
]
```

要点：
- 快照存 `group_name` 与 `image_ids`，发送请求时按 ids 实时取文件路径；素材日后被删除则该任务重跑时报错并提示缺图（历史记录不受影响，仅「重跑」受影响）。
- prompt、源站、参数全部快照进任务行，事后修改/删除 prompt 或源站不影响历史展示。
- 多库内同一张图不允许多次提交（前端控制）；跨库顺序固定为 face → outfit → socks → pose，同库内按 image_ids 顺序展开为 `image[]`。

### 4.2 输出目录规则

```
outputs/
  <安全化的 prompt 名>/
    <yyyyMMdd_HHmmss>_<task_id>/
      <yyyyMMdd_HHmmss>_<序号>.png        # 序号从 1 递增；扩展名按返回 content-type 推断，默认 png
      task.json
```

- `安全化`：去除 `\/:*?"<>|` 与首尾空白，空白串转 `_`，超 80 字符截断（保留扩展语义即可）。
- 不同 prompt 同名 → 落入同一 prompt 目录下不同时间戳子目录，互不覆盖。
- `task.json` 内容：任务全字段快照（含 assets、最终请求的 model/size/quality/n、endpoint、provider 名）+ 每张结果图文件名 + 耗时。人类可读，便于日后脱离本平台检索。

---

## 5. REST API 设计

约定：
- 前缀 `/api`；请求/响应 JSON（上传与生图执行除外）；时间格式 `yyyy-MM-dd HH:mm:ss`。
- 错误响应沿用 FastAPI 默认 `{"detail": "<中文可读信息>"}`，HTTP 状态码 4xx/5xx。
- 分页参数 `page`（1 起）、`size`（默认 50，最大 200）；分页响应 `{"items": [...], "total": 123, "page": 1, "size": 50}`。
- 素材与结果图的浏览器访问走静态挂载：`/files/libraries/<file_path>`、`/files/outputs/<file_path>`（后端把 `DATA_DIR/libraries` 与 `OUTPUT_DIR` 分别挂载为 `/files/libraries`、`/files/outputs`）。

### 5.1 提示词 `/api/prompts`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/prompts?keyword=&tag=&page=&size=` | 列表；keyword 对 name/content/tags 做 LIKE；tag 精确匹配（按逗号拆分后包含） |
| POST | `/api/prompts` | 新建 |
| GET | `/api/prompts/{id}` | 详情 |
| PUT | `/api/prompts/{id}` | 更新 |
| DELETE | `/api/prompts/{id}` | 删除（任务存快照，不影响历史） |

POST/PUT 请求体：

```json
{ "name": "街拍白裙", "content": "A photo of ...", "tags": "街拍,白裙", "remark": "夏季款" }
```

校验：`name` 必填 ≤100 字；`content` 必填 ≤20000 字。`name` 允许重复（输出目录靠时间戳子目录区分）。

GET /api/prompts 响应 items 元素：

```json
{ "id": 12, "name": "街拍白裙", "content": "A photo of ...", "tags": "街拍,白裙",
  "remark": "", "created_at": "2026-09-22 23:15:01", "updated_at": "2026-09-22 23:15:01" }
```

### 5.2 素材库 `/api/libraries/{library}`

`library` ∈ `face | outfit | socks | pose`（非法值 404）。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/libraries/{library}/groups` | 组列表，含 `image_count` |
| POST | `/api/libraries/{library}/groups` | 新建组 `{ "name": "白袜-条纹" }`；同库重名 400 |
| PUT | `/api/libraries/{library}/groups/{group_id}` | 改名/改排序 `{ "name"?, "sort_order"? }` |
| DELETE | `/api/libraries/{library}/groups/{group_id}` | 删组（级联删图片记录 + 磁盘文件） |
| GET | `/api/libraries/{library}/images?group_id=&keyword=` | 图片列表（keyword 匹配 original_name）；带 `url` 字段 |
| POST | `/api/libraries/{library}/images` | multipart：`group_id` + `files[]`（多文件） |
| POST | `/api/libraries/{library}/import-dir` | 服务端批量导入：`{ "source_dir": "D:\\图库\\袜子" }`，见下 |
| PUT | `/api/libraries/{library}/images/{image_id}` | `{ "original_name"?, "group_id"?, "sort_order"? }` |
| DELETE | `/api/libraries/{library}/images/{image_id}` | 删记录 + 磁盘文件 |

响应示例（images 列表元素）：

```json
{ "id": 41, "group_id": 9, "group_name": "白袜-条纹", "library": "socks",
  "original_name": "细节1.png", "file_path": "socks/9/a1b2c3d4_细节1.png", "sort_order": 0,
  "url": "/files/libraries/socks/9/a1b2c3d4_细节1.png", "created_at": "2026-09-22 23:20:11" }
```

**上传规则**：类型白名单 png/jpg/jpeg/webp；单文件 ≤ 20MB；磁盘文件名 `{uuid8}_{原文件名}`（uuid 前缀防碰撞），落至 `DATA_DIR/libraries/<library>/<group_id>/`。

**import-dir 规则**（迁移存量档案的关键）：
- `source_dir` 必须是后端本机存在的绝对路径，否则 400。
- 一级子目录 → 组（目录名即组名，已存在的同名组直接并入）；子目录内图片**递归**导入该组。
- 根级散图 → 自动建组「未分组」（不存在时创建）。
- 响应：`{ "groups_created": 3, "groups_merged": 1, "images_imported": 58, "skipped": 2 }`，`skipped` 为类型不符/超限/无法读取的文件数。

### 5.3 源站 `/api/providers`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/providers` | 列表，返回全部（含停用）；工作台下拉由前端只取 `enabled=true` 的 |
| POST | `/api/providers` | 新建 |
| PUT | `/api/providers/{id}` | 更新 |
| DELETE | `/api/providers/{id}` | 删除（历史快照不受影响） |
| POST | `/api/providers/{id}/test` | 连通性测试 |

POST/PUT 请求体：

```json
{
  "name": "中转站A",
  "type": "openai",
  "base_url": "https://api.example.com",
  "api_key": "sk-xxx",
  "enabled": true,
  "gen_path": "/v1/images/generations",
  "edits_path": "/v1/images/edits",
  "image_field": "image[]",
  "default_model": "gpt-image-1",
  "default_size": "1024x1024",
  "default_quality": "high",
  "timeout_seconds": 300,
  "extra_params": null,
  "param_options": {
    "size": ["1024x1024", "1024x1536", "1536x1024", "auto"],
    "quality": ["auto", "low", "medium", "high"],
    "resolution": ["1K", "2K", "4K"],
    "n_max": 10
  },
  "remark": "主力站"
}
```

`param_options` 是该源站的**参数可选值方案**。不同中转站背后的模型支持的取值不同：有的收像素尺寸（1024x1536），有的只收比例（3:4）；质量有 auto/low/medium/high，也有 standard/hd；清晰度有按 1K/2K/4K 分档的。因此这些下拉的**选项不写死在平台里**，而是每个源站各自配置，工作台按当前所选源站动态渲染；`resolution` 这类非 OpenAI 标准键在生图时通过任务快照的 `extra` 合并进请求参数（见 5.4 / 6.2）。缺省 NULL 时用内置默认：size=[1024x1024, 1024x1536, 1536x1024, auto]、quality=[high, medium, low]、无清晰度项、n_max=10。

`type=mock` 时其余字段可空。`extra_params` 为扁平键值对象，生图时合并进请求参数（表单或 JSON 均适用），值为字符串/数字/布尔。

**test 接口**：`GET {base_url}/v1/models`，超时 5 秒，1 次重试；响应 `{ "ok": true, "status_code": 200, "model_count": 42, "message": "连通正常" }` 或 `{ "ok": false, "message": "<错误摘要>" }`。mock 类型直接返回 ok。**此接口不产生生图费用。**

### 5.4 生图任务 `/api/tasks`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/tasks` | 创建任务（异步执行，立即返回） |
| GET | `/api/tasks?status=&keyword=&prompt_id=&page=&size=` | 历史列表；keyword 匹配 prompt_name/prompt_content |
| GET | `/api/tasks/{id}` | 详情（含结果图 url 列表） |
| POST | `/api/tasks/{id}/rerun` | 以该任务快照新建任务 |
| DELETE | `/api/tasks/{id}` | 删记录（含 task_image），**磁盘文件保留**（防误删成果） |

POST /api/tasks 请求体：

```json
{
  "prompt_id": 12,
  "prompt_name": "街拍白裙",
  "prompt_content": "A photo of ...(编辑器最终文本)",
  "provider_id": 1,
  "model": "gpt-image-1",
  "size": "1024x1536",
  "quality": "high",
  "resolution": "4K",
  "extra": {"resolution": "4K"},
  "n": 2,
  "assets": [
    { "library": "face",   "image_ids": [11] },
    { "library": "outfit", "image_ids": [21, 22, 23] },
    { "library": "socks",  "image_ids": [41] },
    { "library": "pose",   "image_ids": [55, 56] }
  ]
}
```

校验与默认值：
- `prompt_name`、`prompt_content`、`provider_id` 必填；`prompt_id` 可空。
- `assets` 请求体中无需 group 字段，服务端落库快照时按 image_ids 反查并补全 `group_id`/`group_name`（最终快照结构见 4.1）。
- `model/size/quality/n` 空则取 provider 对应默认；`n` ∈ [1, 10]。
- `assets` 各 library 的 `image_ids` 必须真实存在于对应库（且属于该库），否则 400 并指明哪张缺失。
- `extra` 可选，扁平键值对（如清晰度 `{"resolution":"4K"}`，键名/取值范围由源站 param_options 约定）；生图时与标准参数合并发送，并随任务快照存入 `gen_task.extra`，重跑时还原。`resolution` 是前端渲染出来的快捷下拉，最终以 `extra` 为准。
- 判定 endpoint：所有 `image_ids` 合计为空 → `generations`；否则 → `edits`。

响应 `202`：`{ "id": 88, "status": "pending" }`

GET /api/tasks/{id} 响应：

```json
{
  "id": 88, "status": "success", "error_message": null,
  "prompt_id": 12, "prompt_name": "街拍白裙", "prompt_content": "...",
  "provider_id": 1, "provider_name": "中转站A",
  "endpoint": "edits", "model": "gpt-image-1", "size": "1024x1536", "quality": "high", "n": 2,
  "assets": [ ...同快照结构... ],
  "output_dir": "街拍白裙/20260922_231501_88",
  "images": [
    { "id": 301, "file_path": "街拍白裙/20260922_231501_88/20260922_231501_1.png",
      "url": "/files/outputs/街拍白裙/20260922_231501_88/20260922_231501_1.png" }
  ],
  "created_at": "2026-09-22 23:15:01", "started_at": "2026-09-22 23:15:01", "finished_at": "2026-09-22 23:16:20"
}
```

---

## 6. 生图执行流程（generator）

### 6.1 状态机与调度

```
POST /api/tasks ──校验/落库(pending)──▶ 提交 ThreadPoolExecutor(MAX_CONCURRENT_TASKS)
                                          │
worker: pending → running(started_at) ──成功──▶ success(finished_at, output_dir, task_image 落库)
                                          └──任何异常──▶ failed(finished_at, error_message)
```

- 应用启动时把遗留 `pending/running` 置为 `failed`，error_message =「服务重启，任务中断」。
- 并发数来自 `.env`；队列天然由线程池排队。**允许连续提交多个任务**：提交接口立即返回，工作台不锁定，用户可立刻改词换图再提交下一个；进度统一在历史任务页查看（运行中任务由前端每 2 秒轮询刷新状态）。

### 6.2 请求拼接

**edits（选中了素材图）** — `POST {base_url}{edits_path}`，`multipart/form-data`：

| 字段 | 值 |
|---|---|
| `image[]`（字段名取 provider.image_field） | 按第 4.1 节顺序展开的全部选中图片，文件名用 original_name |
| `prompt` | 任务 prompt_content |
| `model` / `n` / `size` | 任务值（size 等取值范围来自该源站 param_options） |
| `quality` | 任务值，空串不传 |
| `extra`（如 resolution） | 任务快照中的附加键，逐项合并 |
| extra_params | 源站配置的固定附加字段，最后合并（与上述键冲突时以 extra_params 为准，便于特殊站覆盖） |

Header：`Authorization: Bearer <api_key>`。

**generations（无素材图）** — `POST {base_url}{gen_path}`，`application/json`：`{prompt, model, n, size, quality?}`（quality 空串同样不传）+ `extra` + extra_params，Header 同上。

**响应处理**：OpenAI 兼容格式 `{"data": [{"b64_json": "..."} | {"url": "..."}]}`。
- `b64_json` → base64 解码写盘。
- `url` → requests 下载（超时 60s，失败重试 1 次）。
- 扩展名按 `Content-Type` 推断（image/png → .png，image/jpeg → .jpg，image/webp → .webp），默认 .png。
- `data` 数量可能少于 n（站点限流部分失败）：有几张存几张，全部存完后若 0 张则任务 failed；否则 success（响应元信息写入 task.json 供核查）。

### 6.3 Mock 源站

- `provider.type = 'mock'`：不走网络。用 Pillow 生成与请求 size 一致的占位图：底色浅灰，写 prompt 前 60 字、model、size、时间戳；sleep 2 秒模拟耗时；组装为与真实响应同构的 `data[0].b64_json`，进入与真实源站完全相同的落盘/状态机逻辑。
- 系统初始化时若无任何 provider，自动创建一条「Mock 本地源站（不消耗额度）」，enabled=1。

---

## 7. 前端设计

视觉基线：Element Plus 默认风格，简单清晰、点按路径短；不做花哨动效。中文界面。

### 7.1 生图工作台 `Workbench.vue`（首页）

三栏布局，纵向撑满整个视口；**不设全局底部运行条**，任务进度统一在历史任务页查看：

```
┌────────────┬──────────────────────────────┬────────────────┐
│ 素材 约300px │ 提示词（居中、最宽）            │ 源站与参数 约300px│
│ 四张选择卡   │ 下拉选择 + 编辑器               │ 动态参数下拉      │
│ 已选缩略图条 │ + 查找/替换工具条               │ 提交前检查卡      │
│ 〔选择…〕    │ + 字数/保存回库                │ 〔生成〕按钮      │
└────────────┴──────────────────────────────┴────────────────┘
```

- **素材列（窄）**：人脸/服装/袜子/姿势四张选择卡纵向排列。实际使用中人脸/袜子/姿势通常各选 1 张、服装最多 3 张，因此素材列整体压窄，把横向空间让给提示词编辑器。每卡：库色点 + 名称 + 已选数量 +〔选择…〕；已选缩略图条带顺序徽标（即 `image[]` 顺序），可移除。
- **提示词列（居中最宽）**：搜索/选择下拉 + 编辑器（本次任务可自由修改，不回写库）+ 局部查找/替换工具条 + 字数统计 +〔另存为新提示词〕〔保存回提示词库〕。
- **PromptEditor（核心组件，必须实现局部查找/替换）**：
  - 工具条：查找输入框、上一个/下一个、匹配计数 `当前/总数`、替换输入框、〔替换〕〔全部替换〕。
  - 实现：纯文本 textarea + 正则循环定位 + `setSelectionRange` 选中当前匹配 + 调整 `scrollTop` 使其可见（textarea 原生选区即高亮）。
  - 大小写不敏感（默认）；「全部替换」一次完成并弹 toast 显示替换次数。
  - 「保存回提示词库」：已选 prompt → PUT 回写；未选 → 弹框输入名称另存为新 prompt。
- **参数列**：源站下拉（**决定下方可选项**）、模型；尺寸 / 质量 / 清晰度下拉的选项来自该源站的 `param_options`，清晰度仅在该站配置了才渲染；张数上限 `n_max`。提交前检查卡：发送方式（edits·参考图 N 张 / generations）、提示词名与字数、目标源站、参数一览；Mock 源站显示「仅联调」警示。生成按钮在缺提示词或未选源站时禁用，并**注明原因**。
- **多任务**：点生成 → POST /api/tasks → toast「任务 #N 已加入队列」后**立即解锁界面**，可改词换图连续提交下一个任务；工作台不展示进度。

### 7.2 AssetPicker 抽屉（四库通用）

- 左侧：组列表（当前库），支持新建/改名/删除；选中组过滤右侧。
- 右侧：图片网格（缩略图 + original_name），点选多选（选中打勾描边）；顶部搜索框按名称过滤。
- 底部：〔确定〕〔取消〕+ 已选计数；确定后按点选顺序返回 image_ids。
- 已在任务中的图片进入抽屉时保持勾选态。

### 7.3 提示词管理 `Prompts.vue`

- 列表页：搜索框（keyword）+ 表格（名称、标签、内容摘要、更新时间）+ 新建/编辑对话框（name/tags/content/remark）+ 删除（二次确认）。
- content 用等宽/多行文本域编辑。

### 7.4 素材库管理 `Libraries.vue`

- 顶部 el-tabs：人脸 / 服装 / 袜子 / 姿势。
- 每库：左侧组树（新建/改名/删除，显示每组图片数）+ 右侧图片网格（悬浮操作：改名 / 移动到其他组 / 删除）。
- 工具栏：〔上传图片〕（多选文件）〔导入磁盘目录〕（弹窗填绝对路径，显示导入统计结果）。
- 上传/导入/删除均即时刷新网格。

### 7.5 源站管理 `Providers.vue`

- 表格：名称、类型、base_url、默认模型、启用、备注 + 行操作（编辑/测试/删除）。
- 编辑抽屉：第 5.3 节全部字段；`type=mock` 时 URL/Key 输入框禁用。
- 〔测试〕行内按钮 → 显示 ok/失败信息。

### 7.6 历史任务 `History.vue`

- 筛选：状态下拉 + 关键字 + 分页表格：创建时间、prompt 名、源站、endpoint、model、n、状态（pending 转圈/failed 红）。
- **pending/running 任务由前端每 2 秒轮询刷新状态**，无需手动刷新页面。
- 详情抽屉：完整参数快照（含各库已选图缩略图）+ 结果图网格（点击大图、单张下载按钮）+ 〔用同样配置重跑〕；失败时红条展示 error_message。
- 删除记录：二次确认，注明「磁盘文件保留在 outputs 目录」。

---

## 8. 错误处理约定

| 场景 | 行为 |
|---|---|
| MySQL 连不上/无权限建库 | 启动失败，终端打印手工建库 SQL 与检查提示 |
| 上传非法类型/超 20MB | 400，逐文件返回原因 |
| import-dir 路径不存在 | 400「后端机器上不存在该目录」 |
| 生图 HTTP 非 200 | 任务 failed，error_message 截取响应体前 2000 字（含状态码） |
| 生图超时 | 按 provider.timeout_seconds 中断，failed「请求超时」 |
| 结果 url 下载失败（重试 1 次后） | 该张跳过；0 张成功则 failed，否则 success 并在 task.json 标注缺失 |
| 重跑时素材已被删 | 任务 failed，error 指明缺失的 library/group/图片名 |
| prompt 名含非法字符 | 落盘前安全化（见 4.2），数据库原名保留 |

---

## 9. 测试策略

- **pytest**（`tests/`），使用独立测试库 `image_gen_platform_test`（conftest 自建自删），`httpx` + FastAPI `TestClient`。
- 覆盖：提示词 CRUD/搜索；组与图片上传/导入/删除（含磁盘文件清理断言）；源站 CRUD；**任务全流程**（Mock 源站：创建 → 轮询 success → 断言输出目录/task.json/task_image）；adapter 单测（伪造 requests 响应：b64_json、url、非 200、超时、部分缺失）；素材缺失重跑分支。
- 网络类测试全部走 Mock/伪造，**不发任何真实外部请求**。
- 前端不写自动化测试，由用户按第 7 节交互自测。

## 10. 验收口径

1. `python run.py` 一键启动（用户配好 `.env` 后），浏览器进入工作台。
2. 用 Mock 源站完成一次完整生成：选 prompt → 编辑器改词并查找替换 → 四库各选图 → 生成 → 历史里看到结果图与输出目录。
3. 用户填入真实中转站，自测连通与出图（平台方不代测）。
