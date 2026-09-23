# AI 生图工作台 — finesse brief

register: product（工作台 · 电脑端 + AI 运行能力层 ai-console）
one-liner: 单人使用的本地生图工作台——提示词 + 四类参考图（人脸/服装/袜子/姿势）组合，经 OpenAI 兼容中转站出图，产出按提示词归档。

## Users & context
单人电商摄影从业者，自己的电脑、自己的浏览器、长时间使用；核心动作是"盯图片"——缩略图与结果图的色彩判断是日常操作，深色界面让图片更准（Lightroom 同理）。高频重复：选词、改词、选图、生成、回看。

## Brand personality
soul: 摄影暗房 · 克制可靠（amber on warm charcoal）
voice: 直接、工具感、不废话；界面文案短句，数据用等宽字体

## Locked dials (project defaults)
SOUL: 6   SPECTACLE: 2   DENSITY: 7

## Visual lock
accent: 森林绿 #2F6B4F（quiet luxury 用法：主按钮/激活导航/选中环，其余页面近乎无彩），on-accent 暖白
theme: 统一暖纸浅色、无深色轨——page #f3f1ec / bg #fbfaf7 / panel-2 #eceae3，暖近黑文字 #26221b；层次靠字重、留白与细线，不靠色块
type: 系统 sans（-apple-system/Segoe UI/微软雅黑）+ 等宽（Cascadia Mono/Consolas）用于路径、时间戳、参数

## Anti-references (must NOT look like)
- first-order: 平台蓝 SaaS 管理后台（#3B82F6 蓝 + 白卡片 + 图表堆砌）
- second-order: AI 紫光晕（near-black + violet glow + 渐变字）——ai-console.md 点名否决的默认
- 暖棕/琥珀深色底（第一版已否决：网页端显旧显脏）
- 青绿浅底 + 深色侧栏的双色壳（第二版已否决：用户不欣赏深浅拼切，要统一面）
- 不做花哨动效：动效只表达状态反馈，整页唯一常驻动画是运行中的心跳点

## Notes
- 四库功能色是语义色不是装饰（暖纸底变体）：人脸 rose #B4485E / 服装 陶土 #C4633F / 袜子 天蓝 #0E7FA8 / 姿势 紫 #7C3F9E，低剂量使用（色点、缩略图边、选中环）
- 语义色独立于品牌色：--up #2E7D5B 成功 / --down #BF4B42 失败 / 运行中用主色心跳点
- 实现阶段映射 Element Plus，token 通过 CSS 变量对齐（accent → --el-color-primary 等）
- 工作台三栏：素材窄列（人脸/袜子/姿势各 1 张、服装最多 3 张）| 提示词居中最宽 | 参数列；不留底部运行条
- 进度查看收敛到历史任务页：提交即入队并立即解锁界面，可连续提交多个任务；历史页对排队/生成中任务每 2 秒轮询刷新
