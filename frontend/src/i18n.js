import { computed, reactive } from 'vue'

/* 轻量中英切换：键 = 中文原文，EN 字典给英文；未命中的键回落中文原文。
 * L('生成 {n} 张', { n: 2 }) 支持插值。locale 持久化到 localStorage.locale。 */

const EN = {
  '生图工作台': 'Workbench',
  '提示词库': 'Prompt Library',
  '素材库': 'Asset Library',
  'API 源站': 'API Providers',
  '历史任务': 'History',
  '提示词': 'Prompt',
  '名称': 'Name',
  '类型': 'Type',
  '默认模型': 'Default Model',
  '启用': 'Enabled',
  '连通性': 'Connectivity',
  '操作': 'Actions',
  '创建时间': 'Created At',
  '源站': 'Provider',
  '方式': 'Mode',
  '结果': 'Result',
  '状态': 'Status',
  '内容摘要': 'Content Preview',
  '标签': 'Tags',
  '更新时间': 'Updated At',
  '测试': 'Test',
  '未测试': 'Untested',
  '编辑': 'Edit',
  '删除': 'Delete',
  '删除记录': 'Delete Record',
  '详情': 'Detail',
  '重跑': 'Rerun',
  '新建源站': 'New Provider',
  '新建提示词': 'New Prompt',
  '新建组': 'New Group',
  '新建素材库': 'New Library',
  '用起来': 'Use',
  '上传图片': 'Upload',
  '导入磁盘目录': 'Import from Disk',
  '管理库': 'Manage Libraries',
  '保存': 'Save',
  '取消': 'Cancel',
  '确定': 'OK',
  '完成': 'Done',
  '上一页': 'Prev',
  '下一页': 'Next',
  '全部组': 'All Groups',
  '清空该库': 'Clear',
  '选择…': 'Pick…',
  '替换': 'Replace',
  '全部替换': 'Replace All',
  '查找': 'Find',
  '另存为新提示词': 'Save as New',
  '保存回提示词库': 'Save to Library',
  '源站与参数': 'Provider & Params',
  '模型': 'Model',
  '比例': 'Ratio',
  '清晰度': 'Resolution',
  '质量': 'Quality',
  '生成张数': 'Count',
  '提交前检查': 'Precheck',
  '发送方式': 'Endpoint',
  '目标': 'Target',
  '参数': 'Params',
  '生成 {n} 张': 'Generate {n}',
  '提交中…': 'Submitting…',
  '排队中': 'Queued',
  '生成中': 'Running',
  '成功': 'Success',
  '部分成功': 'Partial',
  '失败': 'Failed',
  '全部状态': 'All Status',
  '共 {n} 条': '{n} records',
  '第 {p}/{c} 页': 'Page {p}/{c}',
  '第 {p}/{c} 页 · 共 {n} 张': 'Page {p}/{c} · {n} images',
  '共 {n} 张': '{n} images',
  '搜索名称、内容、标签…': 'Search name, content, tags…',
  '搜索提示词名 / 内容…': 'Search prompt name / content…',
  '请先选择或填写提示词': 'Select or enter a prompt first',
  '请选择 API 源站': 'Select an API provider first',
  '✓ {n} 个模型可用': '✓ {n} models available',
  '选择{name}参考图': 'Pick {name} assets',
  '请选择 API 源站 ': 'Select an API provider first ',
}

const state = reactive({ locale: localStorage.getItem('locale') === 'en' ? 'en' : 'zh' })

export const locale = computed({
  get: () => state.locale,
  set: v => { state.locale = v; localStorage.setItem('locale', v) },
})

/* 翻译：zh 为键（未命中回落键本身），vars 做 {k} 插值。模板中调用以获得语言切换的响应性。 */
export function L(zh, vars) {
  let s = state.locale === 'en' ? (EN[zh] ?? zh) : zh
  if (vars) for (const k in vars) s = s.split(`{${k}}`).join(String(vars[k]))
  return s
}
