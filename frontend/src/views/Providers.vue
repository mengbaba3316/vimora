<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { providersApi } from '../api'
import BuildTag from '../components/BuildTag.vue'

/* ── 列表（全量含停用）── */
const list = ref([])
const loading = ref(false)

function errMsg(e) {
  const d = e?.response?.data?.detail
  return typeof d === 'string' ? d : (e?.message || '未知错误')
}
function asList(data) {
  return Array.isArray(data) ? data : (data?.items || [])
}

async function load() {
  loading.value = true
  try {
    const { data } = await providersApi.list()
    list.value = asList(data)
  } catch (e) {
    list.value = []
    ElMessage.error('加载源站失败：' + errMsg(e))
  } finally {
    loading.value = false
  }
}

/* PUT 请求体：按规格 §5.3 全字段（api_key 只在明确填写时携带，避免把已存 Key 清空） */
function rowPayload(p, extra = {}) {
  return {
    name: p.name,
    type: p.type || 'openai',
    base_url: p.base_url || '',
    enabled: !!p.enabled,
    gen_path: p.gen_path || '/v1/images/generations',
    edits_path: p.edits_path || '/v1/images/edits',
    image_field: p.image_field || 'image[]',
    default_model: p.default_model || 'gpt-image-1',
    default_size: p.default_size || '1024x1024',
    default_quality: p.default_quality ?? '',
    timeout_seconds: p.timeout_seconds ?? 300,
    mode: p.mode || 'sync',
    task_query_path: p.task_query_path || '',
    poll_interval_seconds: p.poll_interval_seconds ?? 10,
    extra_params: p.extra_params ?? null,
    param_options: p.param_options ?? null,
    remark: p.remark || '',
    ...extra,
  }
}

/* ── 启停：停用后工作台不再可选 ── */
async function toggle(p) {
  const enabled = !!p.enabled
  try {
    await providersApi.update(p.id, rowPayload(p, { enabled }))
    ElMessage.success(enabled ? `已启用「${p.name}」` : `已停用「${p.name}」，工作台不再可选`)
  } catch (e) {
    p.enabled = !enabled /* 回滚开关 */
    ElMessage.error('修改失败：' + errMsg(e))
  }
}

/* ── 连通性测试：结果按 provider id+updated_at 存 localStorage（不建表），
 * 切页/刷新后仍显示；源站被编辑（updated_at 变化）自然失效重测 ── */
const TKEY = 'providerTestResults'
const testing = reactive({})

function loadTestResults() {
  try { return JSON.parse(localStorage.getItem(TKEY) || '{}') } catch { return {} }
}
const testStore = reactive(loadTestResults())
function resultKey(p) { return `${p.id}:${p.updated_at || ''}` }
function saveTestResults() {
  try { localStorage.setItem(TKEY, JSON.stringify(testStore)) } catch { /* 隐私模式忽略 */ }
}
function testState(p) {
  if (testing[p.id]) return { k: 'testing' }
  const r = testStore[resultKey(p)]
  if (r) return { k: r.ok ? 'ok' : 'bad', text: r.text }
  return { k: 'untested' }
}

async function test(p) {
  testing[p.id] = true
  try {
    const { data } = await providersApi.test(p.id)
    const text = data.ok
      ? `✓ ${data.status_code ?? 200} · ${data.model_count ?? 0} 个模型可用`
      : `✗ ${data.message || '测试失败'}`
    testStore[resultKey(p)] = { ok: !!data.ok, text }
    saveTestResults()
  } catch (e) {
    testStore[resultKey(p)] = { ok: false, text: `✗ ${errMsg(e)}` }
    saveTestResults()
  } finally {
    testing[p.id] = false
  }
}

/* ── 编辑抽屉：规格 §5.3 全字段 ── */
const drawer = ref(false)
const saving = ref(false)
const editId = ref(null)

function blankForm() {
  return {
    name: '', type: 'openai', base_url: '', api_key: '',
    gen_path: '/v1/images/generations', edits_path: '/v1/images/edits', image_field: 'image[]',
    default_model: 'gpt-image-1', default_size: '1024x1024', default_quality: 'high',
    timeout_seconds: 300, mode: 'sync', task_query_path: '', poll_interval_seconds: 10,
    extraText: '', optionsText: '', modelsText: '', remark: '', enabled: true,
  }
}
const form = ref(blankForm())
const isMock = computed(() => form.value.type === 'mock')

function jsonText(v) {
  return v == null ? '' : JSON.stringify(v, null, 2)
}

function openCreate() {
  editId.value = null
  form.value = blankForm()
  drawer.value = true
}

function openEdit(p) {
  editId.value = p.id
  form.value = {
    name: p.name || '',
    type: p.type || 'openai',
    base_url: p.base_url || '',
    api_key: p.api_key || '', /* 列表若不回传 Key 则留空，保存时空值不提交 */
    gen_path: p.gen_path || '/v1/images/generations',
    edits_path: p.edits_path || '/v1/images/edits',
    image_field: p.image_field || 'image[]',
    default_model: p.default_model || 'gpt-image-1',
    default_size: p.default_size || '1024x1024',
    default_quality: p.default_quality ?? 'high',
    timeout_seconds: p.timeout_seconds ?? 300,
    mode: p.mode || 'sync',
    task_query_path: p.task_query_path || '',
    poll_interval_seconds: p.poll_interval_seconds ?? 10,
    extraText: jsonText(p.extra_params),
    optionsText: jsonText(p.param_options),
    modelsText: (Array.isArray(p.param_options?.models) ? p.param_options.models : []).join(', '),
    remark: p.remark || '',
    enabled: !!p.enabled,
  }
  drawer.value = true
}

/* 解析抽屉里的 JSON 文本框，空串 → null */
function parseJson(text, label) {
  const t = (text || '').trim()
  if (!t) return { ok: true, value: null }
  try {
    const v = JSON.parse(t)
    if (typeof v !== 'object' || v === null || Array.isArray(v)) {
      return { ok: false, value: null, msg: `${label}需要是 JSON 对象` }
    }
    return { ok: true, value: v }
  } catch {
    return { ok: false, value: null, msg: `${label}不是合法的 JSON` }
  }
}

/* 可选模型：逗号（含中文逗号）分隔，去首尾空格与空项 */
function parseModels(text) {
  return (text || '').split(/[,，]/).map(s => s.trim()).filter(Boolean)
}

async function save() {
  const f = form.value
  if (!f.name.trim()) { ElMessage.warning('名称必填'); return }
  if (f.mode === 'async' && !f.task_query_path.trim()) {
    ElMessage.warning('异步模式必须填写任务查询路径（如 /api/image-tasks）'); return
  }
  const extra = parseJson(f.extraText, '附加参数 JSON')
  if (!extra.ok) { ElMessage.warning(extra.msg); return }
  const options = parseJson(f.optionsText, '参数可选值方案 JSON')
  if (!options.ok) { ElMessage.warning(options.msg); return }
  /* 可选模型表单字段为准：非空覆盖 param_options.models，留空移除该键（=仅默认模型）；
     其余 JSON 键保留，用户手改 JSON 与表单字段冲突时以表单字段为准 */
  const models = parseModels(f.modelsText)
  let optionsValue = options.value
  if (models.length) optionsValue = { ...(optionsValue || {}), models }
  else if (optionsValue) delete optionsValue.models
  if (optionsValue && !Object.keys(optionsValue).length) optionsValue = null

  const payload = rowPayload(
    { ...f, name: f.name.trim(), timeout_seconds: Number(f.timeout_seconds) || 300,
      poll_interval_seconds: Number(f.poll_interval_seconds) || 10,
      task_query_path: (f.task_query_path || '').trim() },
    { extra_params: extra.value, param_options: optionsValue },
  )
  if (f.api_key.trim()) payload.api_key = f.api_key.trim()
  else if (!editId.value) payload.api_key = ''

  saving.value = true
  try {
    if (editId.value) {
      await providersApi.update(editId.value, payload)
      ElMessage.success('已保存')
    } else {
      await providersApi.create(payload)
      ElMessage.success('已创建')
    }
    drawer.value = false
    await load()
  } catch (e) {
    ElMessage.error('保存失败：' + errMsg(e))
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="view">
    <div class="view-head">
      <h1>API 源站</h1><span class="sub">OpenAI 兼容中转站，路径与默认参数可按站覆盖</span>
      <div class="right">
        <BuildTag />
        <button class="btn primary" @click="openCreate">新建源站</button>
      </div>
    </div>
    <div class="view-body">
      <div class="card table-card" v-loading="loading">
        <table>
          <thead>
            <tr>
              <th style="width:140px">名称</th>
              <th style="width:130px">类型</th>
              <th>Base URL</th>
              <th style="width:170px">默认模型</th>
              <th style="width:64px">启用</th>
              <th style="width:200px">连通性</th>
              <th style="width:110px"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in list" :key="p.id">
              <td>
                <span class="name">{{ p.name }}</span>
                <div v-if="p.remark" class="remark">{{ p.remark }}</div>
              </td>
              <td>
                <span class="chip mute">{{ p.type === 'mock' ? 'mock' : 'openai' }}</span>
                <span v-if="p.mode === 'async'" class="chip mute" title="202 + task_id 轮询取图">异步</span>
              </td>
              <td class="mono-cell">{{ p.base_url || '—' }}</td>
              <td class="mono-cell">{{ p.default_model }}</td>
              <td><el-switch v-model="p.enabled" @change="toggle(p)" /></td>
              <td>
                <div class="test-cell">
                  <button class="btn sm" :disabled="!p.enabled || testing[p.id]" @click="test(p)">测试</button>
                  <span v-if="testing[p.id]" class="testing">请求中…</span>
                  <span v-else-if="testState(p).k === 'ok' || testState(p).k === 'bad'"
                        class="test-result" :class="testState(p).k === 'ok' ? 'ok' : 'bad'">{{ testState(p).text }}</span>
                  <span v-else class="chip mute">未测试</span>
                </div>
              </td>
              <td>
                <div class="ops-cell">
                  <button class="btn sm" @click="openEdit(p)">编辑</button>
                </div>
              </td>
            </tr>
            <tr v-if="!list.length && !loading">
              <td colspan="7">
                <div class="empty"><b>还没有源站</b><p>新建一个 OpenAI 兼容中转站，或先建 Mock 本地源站联调。</p></div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="test-note">连通性测试请求 <span class="num">{base_url}/v1/models</span>，免费接口，不消耗生图额度。真实出图请自行小额度试跑。</p>
    </div>

    <el-drawer v-model="drawer" size="560px" class="prov-drawer" :title="editId ? `编辑「${form.name}」` : '新建源站'">
      <div class="drawer-body">
        <div class="snap-grid">
          <label class="field" style="margin:0"><span>名称 <i class="req">*</i></span>
            <input class="input" v-model="form.name" placeholder="中转站A">
          </label>
          <label class="field" style="margin:0"><span>类型</span>
            <select class="select" v-model="form.type">
              <option value="openai">OpenAI 兼容</option>
              <option value="mock">Mock 本地（联调）</option>
            </select>
          </label>
        </div>
        <label class="field"><span>Base URL</span>
          <input class="input" v-model="form.base_url" :disabled="isMock" placeholder="https://api.example.com（不带 /v1）">
        </label>
        <label class="field"><span>API Key</span>
          <input class="input" v-model="form.api_key" type="password" :disabled="isMock" placeholder="sk-…（仅存本地 SQLite/MySQL）" autocomplete="new-password">
        </label>
        <div class="snap-grid">
          <label class="field" style="margin:0"><span>生图路径（generations）</span>
            <input class="input num" v-model="form.gen_path">
          </label>
          <label class="field" style="margin:0"><span>编辑路径（edits）</span>
            <input class="input num" v-model="form.edits_path">
          </label>
          <label class="field" style="margin:0"><span>多图字段名</span>
            <input class="input num" v-model="form.image_field">
          </label>
          <label class="field" style="margin:0"><span>超时（秒）<template v-if="form.mode === 'async'"> · 异步=总等待上限</template></span>
            <input class="input num" v-model.number="form.timeout_seconds" type="number" min="1">
          </label>
          <label class="field" style="margin:0"><span>默认模型</span>
            <input class="input num" v-model="form.default_model">
          </label>
          <label class="field" style="margin:0"><span>默认尺寸</span>
            <input class="input num" v-model="form.default_size">
          </label>
          <label class="field" style="margin:0"><span>默认质量</span>
            <input class="input num" v-model="form.default_quality" placeholder="high（可留空=不传）">
          </label>
          <label class="field" style="margin:0"><span>备注</span>
            <input class="input" v-model="form.remark" placeholder="给这个源站记点什么">
          </label>
        </div>
        <div class="snap-grid">
          <label class="field" style="margin:0"><span>提交模式</span>
            <select class="select" v-model="form.mode" :disabled="isMock">
              <option value="sync">同步（默认，等响应返回）</option>
              <option value="async">异步（202 + task_id 轮询）</option>
            </select>
          </label>
          <label class="field" style="margin:0" v-if="form.mode === 'async'"><span>轮询间隔（秒）</span>
            <input class="input num" v-model.number="form.poll_interval_seconds" type="number" min="1" max="120">
          </label>
        </div>
        <label class="field" v-if="form.mode === 'async'"><span>任务查询路径（必填）</span>
          <input class="input num" v-model="form.task_query_path" placeholder="/api/image-tasks（凭 task_id 轮询取图）">
        </label>
        <label class="field"><span>可选模型（逗号分隔，留空=仅默认模型）</span>
          <input class="input" v-model="form.modelsText" placeholder="gpt-image-1, sora-image（工作台可选、可手输其他）">
        </label>
        <label class="field"><span>附加参数 JSON（随请求合并发送，可留空）</span>
          <textarea class="textarea mono-area" v-model="form.extraText" rows="3" placeholder='{"background":"transparent"}'></textarea>
        </label>
        <label class="field"><span>参数可选值方案 JSON（该站支持的档位，留空用平台默认）</span>
          <textarea class="textarea mono-area" v-model="form.optionsText" rows="4" placeholder='{"ratios":["3:4","16:9"],"resolutions":["1K","2K","4K"],"quality":["standard","hd"],"models":["gpt-image-1"],"n_max":4}'></textarea>
        </label>
        <div class="enable-row">
          <span>启用</span>
          <el-switch v-model="form.enabled" />
          <span class="enable-hint">停用后不出现在工作台可选列表</span>
        </div>
      </div>
      <template #footer>
        <div class="drawer-foot">
          <button class="btn cancel" @click="drawer = false">取消</button>
          <button class="btn primary" :disabled="saving" @click="save">保存</button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style>
/* 抽屉壳对齐原型 .drawer-h/.drawer-b/.drawer-f（drawer teleport 到 body，须用全局作用域） */
.prov-drawer .el-drawer__header{padding:15px 18px;margin-bottom:0;border-bottom:1px solid var(--border);color:var(--ink-1)}
.prov-drawer .el-drawer__title{font-size:14.5px;font-weight:700}
.prov-drawer .el-drawer__body{padding:16px 18px}
.prov-drawer .el-drawer__footer{padding:13px 18px;border-top:1px solid var(--border)}
</style>

<style scoped>
.view{flex:1;min-height:0;display:flex;flex-direction:column}
.remark{font-size:11px;color:var(--ink-3)}
.mono-cell{font-family:var(--mono);font-size:12px}
.test-cell{display:flex;align-items:center;gap:8px}
.testing{font-size:12px;color:var(--ink-3)}
.test-result{font-size:12px;font-family:var(--mono)}
.test-result.ok{color:var(--up)}
.test-result.bad{color:var(--down)}
.test-note{font-size:12px;color:var(--ink-3);margin:12px 0 0}

/* 抽屉内表单 */
.drawer-body{padding:0}
.snap-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px}
.mono-area{font-family:var(--mono);font-size:12px}
.enable-row{display:flex;align-items:center;gap:10px;padding-top:4px;font-size:13px}
.enable-hint{font-size:11.5px;color:var(--ink-3)}
.drawer-foot{display:flex;gap:8px;justify-content:flex-end;width:100%}
</style>
