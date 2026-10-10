<div align="center">

<h1>
  <img src="logo.svg" alt="" width="76" /><br>
  <img src="logo-wordmark.svg" alt="Vimora" width="190" />
</h1>

**Your own prompts, your own assets — ready to grab, ready to combine.**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3-4FC08D?logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)

[![Gitee](https://img.shields.io/badge/Gitee-vimora-C71D23?logo=gitee)](https://gitee.com/menghahayl/vimora)

[简体中文](README.md) | English

</div>

---

![Workbench](screenshots/workbench.png)

## What is it

Vimora is an AI image generation workbench built around **maintaining and reusing your prompts and reference assets**: references go into asset libraries, organized in groups, always at hand; prompts are archived, searchable, editable and reusable in one click; picking images and tweaking words happens on one screen, and submitting queues the job instantly. Images are generated through any OpenAI-compatible relay and archived by prompt. Built with FastAPI + Vue 3 + MySQL, up and running in one command, with a built-in Mock provider so you can walk through the entire flow without spending a cent.

Who it's for: e-commerce photographers and content creators who constantly "pick words, tweak words, pick images, generate, review" — or anyone who wants an image-generation workflow that doesn't depend on a cloud platform and keeps every prompt and asset on their own disk.

## Highlights

- **Reuse your assets** — upload reference images once, keep them grouped and at hand; no more digging through folders every time
- **Treat prompts as assets** — archive, search, tweak and reuse; stop scrolling through chat history for old prompts
- **Keep working while generating** — submit-and-unlock queueing; tweak the prompt and submit again without waiting for results
- **Everything is traceable** — every task keeps a full snapshot; results are archived by day and prompt, ready to compare and rerun
- **No platform lock-in** — images, prompts and records stay on your own machine, immune to cloud throttling, shutdowns and price hikes

## Why Vimora

The daily grind of e-commerce photography is rewriting the same prompt over and over: swap the outfit, swap the scene, swap the pose, generate, compare. In a chat window, every tweak means digging through history; on a cloud platform, your assets and prompts are never really yours.

Vimora turns that repeated routine into a proper workbench: references live in asset libraries ready to grab, prompts are archived and searchable, tasks queue up the moment you submit so you can keep working, and every image and record lands on your own disk and database.

## The name

**Vimora = Vi + mora**. *Vi* comes from *Vision*; *mora* is Latin for "a moment, a pause" — **letting what you see settle into an image**: a quiet, reliable, un-flashy place where you can focus on the images.

## Design principles

- **Clean and tidy** — three panes, one screen for picking images, tweaking words and generating; the graphite-dark theme is tuned for long hours of judging images, and animations only convey state
- **Easy to use** — install and go: no sign-up, no team setup; the Mock provider lets you practice the whole flow for free
- **Easy to maintain** — organize asset and prompt libraries any way you like; no fixed categories — the more you use it, the better it fits your workflow
- **Yours, managed by you** — all data lives in your own database and disk; back it up or take it with you anytime

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

This project is released under the [GNU AGPL-3.0](LICENSE) — free to use, modify, and distribute (commercial use included), but modified versions, and versions offered as a network service, must make their complete source available under the same license.

Copyright (c) 2026 Vimora contributors
