<div align="center">

<img src="logo.svg" alt="Vimora" width="96" />

# Vimora · Image Generation Workbench

**Compose prompts with reference images — your data never leaves your machine.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3-4FC08D?logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)

[![Gitee](https://img.shields.io/badge/Gitee-vimora-C71D23?logo=gitee)](https://gitee.com/menghahayl/vimora)

[简体中文](README.md) | English

</div>

---

<!-- Screenshot placeholder: save your workbench capture as screenshots/workbench.png, commit it, then uncomment the next line -->
<!-- ![Workbench](screenshots/workbench.png) -->

## What is it

Vimora is a **local-first** AI image generation workbench: it combines a prompt with reference images, sends them to any OpenAI-compatible relay, and archives the results by prompt. The asset libraries are built and maintained by you — faces, outfits, scenes, poses or anything else, organized exactly the way you work, with no fixed categories. Built with FastAPI + Vue 3 + MySQL, up and running in one command, with a built-in Mock provider so you can walk through the entire flow **without spending a cent**.

Who it's for: e-commerce photographers and content creators who constantly "pick words, tweak words, pick images, generate, review" — or anyone who wants an image-generation workflow that doesn't depend on a cloud platform and keeps every prompt and asset on their own disk.

## Why Vimora

The daily grind of e-commerce photography is rewriting the same prompt over and over: swap the outfit, swap the scene, swap the pose, generate, compare. In a chat window, every tweak means digging through history; on a cloud platform, your assets and prompts are never really yours.

Vimora turns that repeated routine into a proper workbench: references live in asset libraries ready to grab, prompts are archived and searchable, tasks queue up the moment you submit so you can keep working, and every image and record lands on your own disk and database.

## The name

**Vimora = Vi + mora**. *Vi* comes from *Vision*; *mora* is Latin for "a moment, a pause" — **letting what you see settle into an image**: a quiet, reliable, un-flashy place where you can focus on the images.

## Design principles

- **Your data, your machine** — assets, prompts, tasks and results all live in a local MySQL database and on disk (`data/`, `outputs/`). No cloud accounts; drop the database and it's all gone.
- **Restrained and reliable** — the default graphite-dark theme is tuned for long hours of judging color on screen (same reason Lightroom is dark), animations only convey state, and the only ever-present animation is a heartbeat dot while a task runs.
- **Zero-cost trial** — a built-in Mock provider walks you through the full create-task-to-result flow without spending money or touching the network; it also powers the automated tests.
- **Single user, complete setup** — no sign-up, no team features. Install and use; one machine and one browser is the whole deployment.

## Features

**Workbench**
- Three-pane layout: assets | prompt | parameters — pick images, tweak words, generate, all on one screen
- Submit-and-unlock: tasks queue instantly, submit several in a row without waiting
- Chinese / English UI toggle (top-right, preference persisted)

**Asset libraries**
- Libraries and groups are free to create and self-maintained — no fixed categories, grow them with your workflow
- Manual upload or bulk import from disk folders (first-level subfolder = group)
- Multi-select cards, group filtering, dynamic pagination, resolution-adaptive grid

**Prompts**
- Prompt archive with keyword / tag search and true pagination for large datasets

**Providers & tasks**
- OpenAI-compatible relay management: CRUD, connectivity test (`GET /v1/models`), per-provider concurrency cap
- With reference images it calls the edits endpoint; without, it automatically falls back to generations
- Async task execution, snapshot-based rerun, daily archiving (`outputs/YYYY-MM-DD/`) plus a full JSON snapshot per task
- Task history: status / keyword filters, 2-second polling for running tasks, failures carry the status code and a response-body excerpt

**Interface**
- Graphite-dark / pure-white dual themes plus classic palettes (Bauhaus red, sweet pink, taro purple, starlight blue, apple green), globally bridged into scrollbars and Element Plus variables
- Frosted-glass overlays (drawers / dialogs / toasts), monospace type for data

## Getting started

Two ways to run it: **from source** (below), or a prebuilt Windows exe (in preparation, will be published on the [Releases](https://gitee.com/menghahayl/vimora/releases) page — no Python setup needed).

### Requirements

- Python 3.9+
- Node.js 16+ (frontend dev / build)
- MySQL 8.x (local or reachable remote)

### 1. Start the backend

```bash
pip install -r requirements.txt
cp .env.example .env      # adjust database connection etc. as needed
python run.py             # defaults to http://127.0.0.1:8765
```

The database and tables are created automatically on first start. If your account lacks the `CREATE DATABASE` privilege, run:

```sql
CREATE DATABASE image_gen_platform DEFAULT CHARSET utf8mb4;
```

### 2. Start the frontend

```bash
cd frontend
npm install
npm run dev               # dev mode; /api and /files are proxied to port 8765
```

Open the URL printed in the terminal; API docs are at `http://127.0.0.1:8765/api/docs`.

### 3. Walk the whole flow for free (Mock)

1. In "Providers", create a provider of type **Mock**;
2. In "Libraries", create a group and upload a few reference images;
3. In the workbench, pick assets, write a prompt, select the Mock provider, and submit;
4. In "Task History", poll until `success`; results are archived under `outputs/<date>/` by prompt.

> To generate for real: fill in any OpenAI-compatible relay's base URL and API key in "Providers" — everything else stays the same.

### Configuration

Copy `.env.example` to `.env` and edit as needed (`.env` never overrides existing environment variables):

| Variable | Default | Description |
| --- | --- | --- |
| `DB_HOST` / `DB_PORT` | `127.0.0.1` / `3306` | MySQL address |
| `DB_USER` / `DB_PASSWORD` | `root` / empty | Database credentials (needs CREATE privilege) |
| `DB_NAME` | `image_gen_platform` | Business database |
| `TEST_DB_NAME` | `image_gen_platform_test` | Test database (pytest, auto-created/dropped) |
| `DATA_DIR` | `data` | Root directory for asset libraries |
| `OUTPUT_DIR` | `outputs` | Root directory for generated results |
| `MAX_CONCURRENT_TASKS` | `2` | Per-provider concurrency cap |
| `APP_PORT` | `8765` | Server port |

## Testing

```bash
python -m pytest tests/ -v
```

Tests use the dedicated `TEST_DB_NAME` database and temp directories for files, so real `data/` and `outputs/` are never touched.

## Project structure

```
app/                    # FastAPI backend
├── config.py           # .env / environment configuration
├── database.py         # DB bootstrap, engine/session
├── models.py           # ORM tables (prompt/library/asset_group/asset_image/provider/gen_task/task_image)
├── routers/            # prompts / libraries / providers / tasks
├── services/           # storage (assets) / generator (inference & results) / task_runner / mock_provider
└── utils/              # filename sanitizing, image I/O
frontend/               # Vue 3 + Vite + Element Plus frontend
└── src/theme.css       # dual-theme & palette tokens
tests/                  # pytest regression suite
data/                   # asset libraries (generated at runtime)
outputs/                # generated results (generated at runtime)
```

## What's next

- [ ] Batch rerun and batch export of tasks
- [ ] Prompt variable templates (batch-fill placeholders with references)

> Got an idea? Open an [Issue](https://gitee.com/menghahayl/vimora/issues) or send a PR.

## Contributing

Issues and PRs are welcome: for bugs please include reproduction steps and logs; for UI changes please keep the current restrained motion language and black-and-white base. Run `python -m pytest tests/` before submitting.

## License

This project is released under the [MIT License](LICENSE) — free to use, modify, and distribute (commercial use included), as long as the copyright notice is preserved.

Copyright (c) 2026 Vimora contributors
