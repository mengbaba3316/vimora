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
accent: 靛蓝 #4A46C9（Stripe/Linear-light 的精确感），on-accent 白；只用于主按钮、激活导航、选中环与心跳点
theme: 冷调高透统一浅面——page 冷石灰 #eceff3 / 卡片纯白 #ffffff / 内衬 #f6f7f9，冷近黑文字 #14171c；浮层（抽屉/弹窗/toast/遮罩）用磨砂玻璃 backdrop-blur 表达「高透」；细线分隔，无深色轨
type: 系统 sans（-apple-system/Segoe UI/微软雅黑）+ 等宽（Cascadia Mono/Consolas）用于路径、时间戳、参数

## Anti-references (must NOT look like)
- first-order: 平台蓝 SaaS 管理后台（#3B82F6 蓝 + 白卡片 + 图表堆砌）——注意靛蓝 #4A46C9 是刻意选择的精确色，不是 reflex 蓝
- second-order: AI 紫光晕（near-black + violet glow + 渐变字）；不做 grain/光晕
- 暖棕/琥珀深色底（v1 已否决：网页端显旧显脏）
- 青绿浅底 + 深色侧栏双色壳（v2 已否决：不欣赏深浅拼切）
- 暖纸象牙色 + 森林绿（v3 已否决：暖调显糊，要冷调清晰）
- 不做花哨动效：动效只表达状态反馈，整页唯一常驻动画是运行中的心跳点

## Notes
- 四库功能色是语义色不是装饰（冷底变体）：人脸 rose #C2435B / 服装 橙 #D9642A / 袜子 天蓝 #0E7FA8 / 姿势 紫 #7C3F9E，低剂量使用（色点、缩略图边、选中环）
- 语义色独立于品牌色：--up #1E8A5F 成功 / --down #D0453C 失败 / 运行中用主色心跳点
- 实现阶段映射 Element Plus，token 通过 CSS 变量对齐（accent → --el-color-primary 等）；磨砂浮层用 el-drawer/el-dialog 自定义 class + backdrop-filter 实现
- 工作台三栏：素材窄列（人脸/袜子/姿势各 1 张、服装最多 3 张）| 提示词居中最宽 | 参数列；不留底部运行条
- 进度查看收敛到历史任务页：提交即入队并立即解锁界面，可连续提交多个任务；历史页对排队/生成中任务每 2 秒轮询刷新
