# SDD ledger — plan: docs/superpowers/plans/2026-09-23-frontend.md
# worktree: .worktrees/frontend (branch feature/frontend)
Task 1: complete (commits 624aaf5, review clean; vite.config +server.host 偏离已裁定可接受)
Task 1: minor (deferred): App.vue 硬编码 #fff/mono/11px 应 token 化；rail 216px vs 原型 212px（其余两项已清：.view-head 已提升全局=e2c69ab；模板残留已清+favicon 星形=66bbc77）
Task 2+3: complete (commits e2c69ab, 9d5c9de；Minor 收尾 66bbc77；无头浏览器 45/45 断言 PASS，0 pageerror；API 行为断言留集成期)
Task 2: complete (commits e2c69ab, review clean)
Task 3: complete (commits 9d5c9de..66bbc77, review clean)
Task 2-3: minor (deferred): theme.css 缺 --on-accent/--down-soft 等 token 致少量裸值；.pg-item:hover 计数消失限组项；搜索防抖竞态旧盖新；total 截断 200 无分页 UI（有意取舍）
Task 2-3: 集成首验项：上传 multipart 字段 files 与后端对齐（后端参数名 files，应一致）
Task 4: fix round 1/5 → 跨线转后端修复（Important I-1：api_key 空值/省略语义，后端 update 需实现空=保留；启停 toggle PUT 不带 key 会清 Key；列表回显 api_key 维持规格"原样返回"不改）
Task 5: complete（随任务 4 同轮审查）
Task 4-5: minor (deferred): ProvidersView.vue 文件名与简报 ProvidersView.vue 不符（合理，router 已引用）；.card 未 token 化（值同原型）；连通性列宽 210 vs 200；截图证据记账不严谨；AssetPicker 陈旧 id 不清理
Task 4-5: 集成项 +1：前端「空 api_key=保留」约定依赖后端修复，集成期必须回归验证
Task 6: complete (commits ff19a0d..4251840, review clean)
Task 6: minor (deferred): replaceOne 后 idx 重置 0（简报原文如此）；scrollTop 硬编码 22px；切源站重置 model 覆盖手改；pendingPrompt 指向已删提示词的空白边界
Task 6: 集成项 +1：TaskIn 需容忍显式 null（已转 B6）；历史详情读取 resolution 用 extra.resolution（转 F5）
Task 7: complete (commits 4251840..0aaedd6, review clean)
Task 8: complete（构建通过；main.py 托管按裁定归集成阶段）
Task 7: Important → 集成承接：partial/queued 派生映射（裁定：后端枚举维持规格 DDL 四值，前端 normStatus 派生 success&&ok<n→partial、pending→queued，筛选同步映射）
=== 前端线 8/8 任务完成，等待集成合并 ===
Task 7: complete（1 Important → 集成代理已修：normStatus 派生 + 筛选映射，commit 9c51004）
Task 8: complete（构建通过；托管由集成 commit ca47e22 落地）
Task 7-8: minor (deferred): 清晰度独立快照格布局略异；mini 占位色深；重跑无状态守卫；partial 无 skipNote（数据不支持）
=== 集成完成：ca47e22 SPA 托管 + 9c51004 状态派生 + 1d145fb/79e4f79 收尾；36 passed；浏览器端到端验收通过 ===
