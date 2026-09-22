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
accent: 琥珀 #E8A33D（暗色底）/ #B77A16（浅色底），on-accent 用近黑 #1a1206
theme: dark——暖石色深底（Warm Stone ramp：page #191612 / bg #29241e / panel-2 #3b352d），深底服务于看图，不是装饰
type: 系统 sans（-apple-system/Segoe UI/微软雅黑）+ 等宽（Cascadia Mono/Consolas）用于路径、时间戳、参数

## Anti-references (must NOT look like)
- first-order: 平台蓝 SaaS 管理后台（#3B82F6 蓝 + 白卡片 + 图表堆砌）
- second-order: AI 紫光晕（near-black + violet glow + 渐变字）——ai-console.md 点名否决的默认
- 不做花哨动效：动效只表达状态反馈，整页唯一常驻动画是运行中的心跳点

## Notes
- 四库功能色是语义色不是装饰：人脸 rose / 服装 teal / 袜子 sky / 姿势 violet，低剂量使用（色点、缩略图边、选中环）
- 语义色独立于品牌色：--up #3FCB86 成功 / --down #FF5F56 失败 / 运行中用琥珀心跳
- 实现阶段映射 Element Plus，token 通过 CSS 变量对齐（accent → --el-color-primary 等）
- 三个时态同屏：工作台底部运行条（现在/将来）+ 最近任务（过去），历史页承载完整过去
