# SDD ledger — plan: docs/superpowers/plans/2026-09-23-backend-api.md
# worktree: .worktrees/backend (branch feature/backend)
Task 1: complete (commits 12fb1cf, review folded into task 2 review)
Task 2: fix round 1/5 (1 open — Important: Prompt.content 用 Text 应为 MEDIUMTEXT with_variant，规格§4/全局约束1; app/models.py:17)
Task 1-2: minor (deferred): database.py 死导入 text；test_models 弱断言建议 pytest.raises(IntegrityError)；二级索引/列级 DEFAULT/ON UPDATE 未落 DDL（ORM 等价，暂缓对齐）；db_url 去参理由表述有误（改动本身保留）；run.py 需认领"连不上给手工建库提示"（规格§3，转 B6）
Task 2: fix round 1/5 (1 addressed, 0 open — MEDIUMTEXT; commits 84c5e66..317d79c)
Task 1: complete (commits 0ed52d5..12fb1cf, review clean)
Task 2: complete (commits 12fb1cf..317d79c, 1 fix round, review clean)
Task 3: fix round 1/5 (3 open — Important: update_group 重名 500 应 400; Important: update/delete 组与图片缺 _lib 与归属校验致跨库越权; 规格缺口: PromptOut 缺 created_at/updated_at、缺 tag= 精确匹配参数)
Task 3-4: minor (deferred): uuid_filename 应 basename+安全化防路径字符/超长；上传整读内存；update_image body:dict 无类型校验；PromptOut class Config 弃用告警；created_at str() 依赖无小数秒；测试缺口（非法 library 404/404 类/部分成功/update_image）
Task 3-4: 跟进项 → B6：requirements 补 email-validator>=2.0；create_app 补 storage.DATA_DIR = settings.DATA_DIR
Task 3: fix round 1/5 (4 addressed, 0 open; commits 4f7757e..10af8c5)
Task 3: complete (commits 317d79c..10af8c5, 1 fix round, review clean)
Task 4: complete (commits 4f7757e..10af8c5, review clean)
Task 4: minor (deferred): update_image 的 group_id 白名单仍可移到不存在/跨库组（复审残留，转 B3 顺带修）；tag=",," 空集边缘语义（Minor）
Task 5: complete (commits 10af8c5..6387106, review clean; commit 信息带后缀已裁定 Minor 可接受)
Task 6: complete (commits 10af8c5..c15f56b, review clean)
Task 5-6: minor (deferred): update_image body dict 类型问题致 int(None)/"abc" 500；mimetypes 与 content_type 判定路径不一致（留观）；_one 注解 Optional 误导；ProviderIn.type 无枚举校验（→B6 用 Literal）；import-dir 无隐藏目录排除；二遍导入重复入库（简报如此）
Task 5: fix ruling — 实现者报告偏差②失实已裁定：requests 自 12fb1cf 起即在 requirements，仅缺 email-validator；B6 派单携带正确清单并要求更正报告行
Task 7: complete (commits c15f56b..08b6ded, review clean)
Task 7: minor (deferred): timeout_seconds 无兜底与 paths 不一致（B5 接线留意）；write_task_json 无测试（任务8/10 回归）；test_generator 两个无用导入（简报原文）
Task 6: fix round 1/5 (1 addressed, 0 open — api_key 空=保留；commits c15f56b..8635881)
Task 6: complete (commits 10af8c5..8635881, 1 fix round, review clean)
Task 6: minor (deferred/裁定): PUT 无法显式清空 Key 属预期取舍（与前端约定一致）
Task 8: complete (commits 8635881..edaef82, review clean)
Task 9: complete (commits edaef82..3a4a6de, review clean)
Task 8-9: minor (deferred→B6 承接)：POST 200→202 对齐规格（一行）；TaskIn 容忍显式 null（前端 F4 发显式 null）；_snapshot 补 finished_at/error_message；finally 补 rollback 防护；非 200 响应体截 2000 字入 error（规格§8）；跨库展开顺序后端不强制（前端按固定序发，留观）
Task 10: complete (commits 3a4a6de..195c245, 7 承接项全落实, review clean)
Task 9-10: minor (deferred): task_runner 早退路径 db.close 未关（罕见路径）；建库失败测试依赖 3399 端口空闲；README 建库 SQL 硬编码库名
=== 后端线 10/10 任务完成，等待集成合并 ===
