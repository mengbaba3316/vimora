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
accent: 青绿 #176C6B（Teal & Clay），on-accent 白；partner 陶土 #C4633F 仅作次强调与四库功能色
theme: light 双色壳——内容区浅青灰纸（page #e9eeed / bg #fdfefd / panel-2 #f1f5f4），侧栏深青黑 #0e1a19；网页端工作台要亮堂清楚，看图集中在素材缩略图与结果网格
type: 系统 sans（-apple-system/Segoe UI/微软雅黑）+ 等宽（Cascadia Mono/Consolas）用于路径、时间戳、参数

## Anti-references (must NOT look like)
- first-order: 平台蓝 SaaS 管理后台（#3B82F6 蓝 + 白卡片 + 图表堆砌）
- second-order: AI 紫光晕（near-black + violet glow + 渐变字）——ai-console.md 点名否决的默认
- 暖棕/琥珀深色底（第一版原型已否决：网页端大面积深棕黄显旧显脏；将来若重启深色须避开黄棕相）
- 不做花哨动效：动效只表达状态反馈，整页唯一常驻动画是运行中的心跳点

## Notes
- 四库功能色是语义色不是装饰（浅底变体）：人脸 rose #B4485E / 服装 陶土 #C4633F / 袜子 天蓝 #0E7FA8 / 姿势 紫 #7C3F9E，低剂量使用（色点、缩略图边、选中环）
- 语义色独立于品牌色：--up #2C7A62 成功 / --down #C0453C 失败 / 运行中用主色心跳点
- 实现阶段映射 Element Plus，token 通过 CSS 变量对齐（accent → --el-color-primary 等）
- 工作台三栏：素材窄列（人脸/袜子/姿势各 1 张、服装最多 3 张）| 提示词居中最宽 | 参数列；不留底部运行条
- 进度查看收敛到历史任务页：提交即入队并立即解锁界面，可连续提交多个任务；历史页对排队/生成中任务每 2 秒轮询刷新
