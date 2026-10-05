<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { libsApi, libTypesApi, promptsApi, providersApi, tasksApi } from '../api'
import { ratioToSize } from '../utils/sizeMap'
import { store } from '../store'
import PromptEditor from '../components/PromptEditor.vue'
import AssetPicker from '../components/AssetPicker.vue'
import PaletteButton from '../components/PaletteButton.vue'
import LangButton from '../components/LangButton.vue'
import { L } from '../i18n'

/*
 * 生图工作台（原型 #view-workbench）：
 * 三栏 grid —— 素材列(order 0) | 提示词列(order 1) | 参数列(order 2)。
 * 参数联动：可选值全部来自当前源站 param_options（null 用内置默认）。
 * 提交即入队：POST /tasks 成功 → toast → 界面立即解锁、配置保留，可连续提交。
 */

/* 一级素材库：动态加载「启用」的库（停用的库不进工作台），颜色/排序随配置 */
const libTypes = ref([])

async function loadLibTypes() {
  try {
    const { data } = await libTypesApi.list()
    libTypes.value = asList(data).filter(l => l.enabled)
  } catch {
    libTypes.value = []
  }
}

function errMsg(e) {
  const d = e?.response?.data?.detail
  return typeof d === 'string' ? d : (e?.message || '未知错误')
}
function asList(data) {
  return Array.isArray(data) ? data : (data?.items || [])
}

/* ── 提示词 ── */
const CUSTOM_PROMPT_ID = '__custom__'    /* 下拉里的「自定义 Prompt」哨兵值：临时编写，不入库 */
const prompts = ref([])
const selectedPromptId = ref(null)
const editingPrompt = ref(null)          /* 当前选中的库内提示词（可空=自定义/未选） */
const editorText = ref('')
const promptEditorRef = ref(null)
const isCustomPrompt = computed(() => selectedPromptId.value === CUSTOM_PROMPT_ID)

async function loadPrompts() {
  try {
    const { data } = await promptsApi.list({ size: 500 })
    prompts.value = data.items || []
  } catch {
    prompts.value = []
  }
}

function loadPromptIntoEditor(p) {
  editingPrompt.value = p || null
  editorText.value = p?.content || ''
  promptEditorRef.value?.resetFind()
}
function onPromptChange() {
  if (isCustomPrompt.value) {
    /* 自定义 Prompt：编辑区清空临时编写，不关联库内提示词 */
    editingPrompt.value = null
    editorText.value = ''
    promptEditorRef.value?.resetFind()
    return
  }
  loadPromptIntoEditor(prompts.value.find(x => x.id === selectedPromptId.value))
}
/* PromptEditor 另存成功：刷新列表并选中新提示词 */
async function onPromptSaved(created) {
  await loadPrompts()
  const found = prompts.value.find(x => x.id === created?.id) || created
  if (found) {
    selectedPromptId.value = found.id
    editingPrompt.value = found
  }
}

/* ── 素材：各库选中状态（有序 image_id，按库 id 动态建键）+ id→图元信息（卡片 chip 显示名）── */
const sel = reactive({})
const imgIndex = {}
const pickers = {}

async function indexLibImages() {
  await Promise.all(libTypes.value.map(async (l) => {
    sel[l.id] = sel[l.id] || []
    try {
      const { data } = await libsApi.images(l.id)
      imgIndex[l.id] = new Map(asList(data).map(img => [img.id, img]))
    } catch { /* 索引失败时 chip 退化为显示 #id */ }
  }))
}
function imgName(lib, id) {
  return imgIndex[lib]?.get(id)?.original_name || `#${id}`
}
function removeAsset(lib, id) {
  const i = (sel[lib] || []).indexOf(id)
  if (i > -1) sel[lib].splice(i, 1)
}
const assetsCount = computed(() => libTypes.value.reduce((a, l) => a + (sel[l.id]?.length || 0), 0))

const providers = ref([])                /* 仅 enabled */
/* ── 源站与参数联动（从原型 renderParamOptions 移植）──
 * 两种形态：源站 param_options 配了 size（像素串列表）→ 维持「尺寸」直选；
 * 否则「比例 + 清晰度」档位，提交时按 ratioToSize 换算成像素串。
 */
const DEFAULT_RATIOS = ['1:1', '3:4', '4:3', '16:9', '9:16', '2:3', '3:2']
const DEFAULT_RESOLUTIONS = ['1K', '2K', '3K', '4K']
const form = reactive({ providerId: null, model: 'gpt-image-1', ratio: '3:4', size: '', quality: '', resolution: null, n: 2 })
const sizeMode = ref(false)
const sizeOptions = ref([]), ratioOptions = ref([]), resolutionKs = ref([])
const qualityOptions = ref([]), modelOptions = ref([]), nMax = ref(10)

const currentProvider = computed(() => providers.value.find(p => p.id === form.providerId))

function renderParamOptions() {
  const p = currentProvider.value
  const po = p?.param_options || {}
  qualityOptions.value = po.quality || ['high', 'medium', 'low']
  nMax.value = po.n_max || 10
  sizeMode.value = Array.isArray(po.size) && po.size.length > 0
  if (sizeMode.value) {
    sizeOptions.value = po.size
    form.size = po.size[0]               /* 旧行为：直接选像素串，比例/清晰度隐藏 */
    form.resolution = null
  } else {
    ratioOptions.value = po.ratios?.length ? po.ratios : DEFAULT_RATIOS
    resolutionKs.value = po.resolutions?.length ? po.resolutions : DEFAULT_RESOLUTIONS
    form.ratio = ratioOptions.value.includes('3:4') ? '3:4' : ratioOptions.value[0]
    form.resolution = resolutionKs.value.includes('2K') ? '2K' : resolutionKs.value[0]
  }
  form.quality = qualityOptions.value[0]   /* 默认取第一项（如 high），避免无配置源站落到 low */
  form.n = Math.min(nMax.value, Math.max(1, form.n || 1))
  /* 模型来源优先级：手填白名单（param_options.models）> 测试缓存的全量列表
     （available_models）> 仅默认模型。默认模型始终在列并优先选中，仍可手输其他。 */
  const dm = p?.default_model || 'gpt-image-1'
  const fetched = Array.isArray(p?.available_models) ? p.available_models : []
  let opts
  if (Array.isArray(po.models) && po.models.length) opts = [...po.models]
  else if (fetched.length) opts = [...fetched]
  else opts = [dm]
  if (!opts.includes(dm)) opts.unshift(dm)
  modelOptions.value = opts
  form.model = dm
}
function onProviderChange() { renderParamOptions() }
function nMinus() { form.n = Math.max(1, form.n - 1) }
function nPlus() { form.n = Math.min(nMax.value, form.n + 1) }
function onNInput() { form.n = Math.min(nMax.value, Math.max(1, parseInt(form.n) || 1)) }

/* ── 提交前检查（皆 computed）── */
const ckEndpoint = computed(() => assetsCount.value ? `edits · ${L('参考图 {n} 张', { n: assetsCount.value })}` : `generations · ${L('纯文生图')}`)
const ckPrompt = computed(() => `${editingPrompt.value?.name || (isCustomPrompt.value ? L('自定义') : L('未选择'))} · ${editorText.value.length} ${L('字')}`)
const ckProv = computed(() => currentProvider.value?.name || L('未选择'))
const ckParams = computed(() => sizeMode.value
  ? `${form.size || '-'} · ${form.quality || '-'} · ${form.n} 张`
  : `${form.ratio} · ${form.resolution} · ${form.quality || '-'} · ${form.n} ${L('张')}`)
const isMock = computed(() => currentProvider.value?.type === 'mock')
const genReason = computed(() => {
  const reason = []
  if (!editorText.value.trim()) reason.push(L('请先选择或填写提示词'))
  if (!currentProvider.value) reason.push(L('请选择 API 源站'))
  return reason.join('；')
})

/* ── 生成：提交即入队，成功后立即解锁、配置保留 ── */
const submitting = ref(false)

async function submitTask() {
  if (genReason.value || submitting.value) return
  const ep = assetsCount.value ? 'edits' : 'generations'
  const assets = libTypes.value.filter(l => (sel[l.id]?.length || 0))
    .map(l => ({ library: l.id, image_ids: [...sel[l.id]] }))
  submitting.value = true
  try {
    /* 尺寸：像素模式原样传所选串；比例模式按清晰度档位换算（extra.resolution 带所选 K） */
    const size = sizeMode.value ? form.size : ratioToSize(form.ratio, form.resolution, form.model)
    const { data } = await tasksApi.create({
      prompt_id: editingPrompt.value?.id ?? null,
      prompt_name: editingPrompt.value?.name || (isCustomPrompt.value ? L('自定义') : '未命名'),
      prompt_content: editorText.value,
      provider_id: form.providerId,
      model: form.model,
      size,
      quality: form.quality,
      n: form.n,
      assets: assets.length ? assets : null,
      extra: !sizeMode.value && form.resolution ? { resolution: form.resolution } : null,
    })
    ElMessage.success(`任务 #${data.id} 已加入队列（${ep} · ${form.n} 张），改完词图可继续提交，进度见历史任务页`)
  } catch (e) {
    ElMessage.error('提交失败：' + errMsg(e))
  } finally {
    submitting.value = false   /* 不轮询不阻塞，界面立即解锁，配置保留 */
  }
}

/* ── 挂载：先拉库定义（启用的库），再并行拉提示词 / 源站 / 库图索引；消费 pendingPrompt ── */
onMounted(async () => {
  await loadLibTypes()
  await Promise.all([loadPrompts(), indexLibImages(), (async () => {
    try {
      const { data } = await providersApi.list()
      providers.value = asList(data).filter(p => p.enabled)
    } catch {
      providers.value = []
    }
  })()])

  if (providers.value.length) {
    form.providerId = providers.value[0].id
    renderParamOptions()
  }

  const pending = store.pendingPrompt
  store.pendingPrompt = null
  if (pending) {
    /* 提示词库「用起来」跳转：选中该提示词并载入（可自由修改，不回写库） */
    const found = prompts.value.find(x => x.id === pending.id)
    selectedPromptId.value = found?.id ?? pending.id
    editingPrompt.value = found || { id: pending.id, name: pending.name }
    editorText.value = pending.content || ''
    promptEditorRef.value?.resetFind()
  } else if (prompts.value.length) {
    selectedPromptId.value = prompts.value[0].id
    loadPromptIntoEditor(prompts.value[0])
  } else {
    /* 库里还没有提示词：直接落到自定义模式，编辑区留空即可开写 */
    selectedPromptId.value = CUSTOM_PROMPT_ID
  }
})
</script>

<template>
  <div class="view">
    <div class="view-head">
      <span class="sub">{{ L('选词 → 改词 → 选图 → 生成；任务入队后即可连续提交，进度在历史任务页查看') }}</span>
      <PaletteButton style="margin-left:auto" />
      <LangButton />
    </div>

    <div class="wb">
      <!-- 左(order 0)：素材库卡（仅显示启用的库，颜色/排序随配置） -->
      <section class="col-assets">
        <section v-for="l in libTypes" :key="l.id" class="card lib-card">
          <div class="card-h">
            <span class="ld" :style="{ background: l.color || 'var(--ink-3)' }"></span>
            <b>{{ L('{name}库', { name: l.name }) }}</b>
            <span class="cnt">{{ sel[l.id]?.length ? L('已选 {n} 张', { n: sel[l.id].length }) : L('未选择') }}</span>
            <button class="btn sm pick-btn" @click="pickers[l.id]?.open()">{{ L('选择…') }}</button>
          </div>
          <div class="sel-strip">
            <template v-if="sel[l.id]?.length">
              <span v-for="(id, i) in sel[l.id]" :key="id" class="sel-chip"
                    :style="{ '--tint': l.color, '--tint-solid': l.color }" :title="imgName(l.id, id)">
                <span class="thumb">{{ imgName(l.id, id).slice(0, 2) }}</span>
                <span class="ord num">{{ i + 1 }}</span>
                <button class="rm" title="移除" @click="removeAsset(l.id, id)">✕</button>
              </span>
            </template>
            <span v-else class="empty-hint">{{ L('还没有选择{name}参考图，点「选择…」从库中挑选（可多张）', { name: l.name }) }}</span>
          </div>
        </section>
        <AssetPicker v-for="l in libTypes" :key="l.id" :ref="el => (pickers[l.id] = el)"
                     :library="l.id" :lib-name="l.name" :lib-color="l.color || 'var(--ink-3)'"
                     v-model="sel[l.id]" />
        <div v-if="!libTypes.length" class="card" style="padding:22px;text-align:center;color:var(--ink-3);font-size:12.5px">
          还没有启用的素材库。去「素材库 → 管理库」新建或启用。
        </div>
      </section>

      <!-- 中(order 1)：提示词 -->
      <section class="card col-prompt">
        <div class="card-h"><b>{{ L('提示词') }}</b><span class="cnt">{{ isCustomPrompt ? L('临时编写，不存入提示词库') : L('本次可自由修改，不回写库') }}</span></div>
        <div class="prompt-pick">
          <el-select id="promptSel" v-model="selectedPromptId" class="wselect" placeholder="选择提示词…" @change="onPromptChange">
            <el-option :value="CUSTOM_PROMPT_ID" :label="L('自定义 Prompt')" />
            <el-option v-for="p in prompts" :key="p.id" :value="p.id" :label="p.name" />
          </el-select>
        </div>
        <PromptEditor ref="promptEditorRef" v-model="editorText" :prompt="editingPrompt" @saved="onPromptSaved" />
      </section>

      <!-- 右(order 2)：源站与参数 + 提交前检查 -->
      <aside class="card col-params">
        <div class="card-h"><b>{{ L('源站与参数') }}</b></div>
        <div class="params-body">
          <label class="field"><span>{{ L('API 源站') }} <i class="req">*</i></span>
            <el-select id="provSel" v-model="form.providerId" class="wselect" placeholder="请选择 API 源站" @change="onProviderChange">
              <el-option v-for="p in providers" :key="p.id" :value="p.id"
                         :label="p.name + (p.type === 'mock' ? '（联调）' : '')" />
            </el-select>
            <div v-if="currentProvider?.remark" id="provRemark" class="prov-remark">{{ currentProvider.remark }}</div>
          </label>
          <div class="field"><span>{{ L('模型') }}</span>
            <el-select id="pModel" v-model="form.model" class="wselect" filterable allow-create
                       default-first-option placeholder="选择或输入模型">
              <el-option v-for="m in modelOptions" :key="m" :value="m" :label="m" />
            </el-select>
          </div>
          <label v-if="sizeMode" class="field"><span>尺寸</span>
            <el-select id="pSize" v-model="form.size" class="wselect">
              <el-option v-for="s in sizeOptions" :key="s" :value="s" :label="s" />
            </el-select>
          </label>
          <template v-else>
            <label id="ratioField" class="field"><span>{{ L('比例') }}</span>
              <el-select id="pRatio" v-model="form.ratio" class="wselect">
                <el-option v-for="r in ratioOptions" :key="r" :value="r" :label="r" />
              </el-select>
            </label>
            <label id="resField" class="field"><span>{{ L('清晰度') }}</span>
              <el-select id="pRes" v-model="form.resolution" class="wselect">
                <el-option v-for="r in resolutionKs" :key="r" :value="r" :label="r" />
              </el-select>
            </label>
          </template>
          <label class="field"><span>{{ L('质量') }}</span>
            <el-select id="pQuality" v-model="form.quality" class="wselect">
              <el-option v-for="q in qualityOptions" :key="q" :value="q" :label="q" />
            </el-select>
          </label>
          <label class="field"><span>{{ L('生成张数') }}</span>
            <div class="n-row">
              <button id="nMinus" class="iconbtn" @click="nMinus">−</button>
              <input id="pN" v-model="form.n" class="input num" style="text-align:center;width:64px" @input="onNInput">
              <button id="nPlus" class="iconbtn" @click="nPlus">＋</button>
              <span class="n-hint">{{ L('1 至 {n} 张', { n: nMax }) }}</span>
            </div>
          </label>
        </div>
        <div class="precheck">
          <h4>{{ L('提交前检查') }}</h4>
          <div class="li"><span class="k">{{ L('发送方式') }}</span><b id="ckEp">{{ ckEndpoint }}</b></div>
          <div class="li"><span class="k">{{ L('提示词') }}</span><b id="ckPrompt">{{ ckPrompt }}</b></div>
          <div class="li"><span class="k">{{ L('目标') }}</span><b id="ckProv">{{ ckProv }}</b></div>
          <div class="li"><span class="k">{{ L('参数') }}</span><b id="ckParams" class="num">{{ ckParams }}</b></div>
          <div v-if="isMock" class="warnline">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" style="flex:none;margin-top:2px"><path d="M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z"/></svg>
            <span>Mock 本地源站仅用于联调，不会生成真实图片</span>
          </div>
        </div>
        <div class="gen-wrap">
          <button id="genBtn" class="btn primary gen" :disabled="!!genReason || submitting" @click="submitTask">
            {{ submitting ? L('提交中…') : L('生成 {n} 张', { n: form.n }) }}
          </button>
          <div id="genReason" class="gen-reason" :class="{ on: !!genReason }">{{ genReason }}</div>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.view{flex:1;min-height:0;display:flex;flex-direction:column}

/* 三栏 grid：素材(窄) | 提示词(宽) | 参数（原型 .wb） */
.wb{flex:1;min-height:0;display:grid;grid-template-columns:302px minmax(0,1fr) 300px;gap:14px;padding:14px 22px 16px}
.wb>*{min-height:0}

.card-h{display:flex;align-items:center;gap:9px;padding:13px 16px;border-bottom:1px solid var(--border);flex:none}
.card-h b{font-size:13.5px;font-weight:700}
.card-h .cnt{margin-left:auto;font-size:11.5px;color:var(--ink-3)}
.card-h .ld{width:9px;height:9px;border-radius:50%;flex:none}

/* 提示词列 */
.col-prompt{order:1;display:flex;flex-direction:column;min-height:0}
.prompt-pick{padding:12px 16px 4px}
.prompt-pick .select{font-weight:600}

/* 素材列（order 0 在 DOM 前，order 声明保持与原型一致） */
.col-assets{order:0;display:flex;flex-direction:column;gap:12px;overflow-y:auto;padding-right:2px}
.lib-card{flex:none}
.lib-card .pick-btn{margin-left:auto}
.sel-strip{display:flex;gap:8px;padding:11px 16px 14px;flex-wrap:wrap;min-height:14px}
.sel-strip .empty-hint{font-size:12px;color:var(--ink-3)}
.sel-chip{position:relative;width:40px;height:40px;border-radius:8px;flex:none;border:1.5px solid var(--tint-solid)}
.sel-chip .thumb{width:100%;height:100%;border-radius:inherit;display:grid;place-items:center;font-size:10px;font-weight:700;letter-spacing:.05em;color:var(--ink-2);background:linear-gradient(135deg,var(--tint),transparent 140%),var(--panel-2);border:1px solid var(--border)}
.sel-chip .rm{position:absolute;top:-6px;right:-6px;width:16px;height:16px;border-radius:50%;background:var(--panel-3);color:var(--ink-2);font-size:10px;display:none;place-items:center;border:1px solid var(--border-2);cursor:pointer}
.sel-chip:hover .rm{display:grid}
.sel-chip .ord{position:absolute;bottom:-5px;right:-5px;min-width:15px;height:15px;padding:0 3px;border-radius:99px;background:var(--accent);color:var(--on-accent);font-size:9.5px;font-weight:700;display:grid;place-items:center;font-family:var(--mono)}

/* 参数列 */
.col-params{order:2;display:flex;flex-direction:column;min-height:0;overflow:hidden}
.params-body{padding:13px 16px;flex:1;min-height:0;overflow-y:auto}
.prov-remark{margin-top:6px;font-size:12px;color:var(--ink-3);line-height:1.45}

.n-row{display:flex;gap:6px;align-items:center}
.n-hint{font-size:11.5px;color:var(--ink-3)}
.iconbtn{width:26px;height:26px;border-radius:8px;display:grid;place-items:center;color:var(--ink-2);flex:none;border:1px solid var(--border);background:none;cursor:pointer;font-family:inherit}
.iconbtn:hover{background:var(--panel-3);color:var(--ink-1)}

/* 提交前检查 + 生成 */
.precheck{flex:none;margin:4px 16px 12px;background:var(--panel-2);border:1px solid var(--border);border-radius:11px;padding:11px 13px}
.precheck h4{font-size:11px;letter-spacing:.1em;color:var(--ink-3);font-weight:700;margin:0 0 8px}
.precheck .li{display:flex;gap:8px;font-size:12px;color:var(--ink-2);padding:2.5px 0}
.precheck .li b{color:var(--ink-1);font-weight:600;min-width:0}
.precheck .li .k{color:var(--ink-3);flex:none;width:62px}
.warnline{margin-top:7px;padding-top:7px;border-top:1px dashed var(--border-2);color:var(--warn);font-size:11.5px;display:flex;gap:6px;align-items:flex-start}
.gen-wrap{flex:none;padding:0 16px 16px}
.btn.gen{width:100%;padding:11px;font-size:14.5px;font-weight:700;border-radius:11px;box-shadow:0 8px 24px var(--glow)}
.gen-reason{font-size:11.5px;color:var(--down);margin-top:7px;display:none}
.gen-reason.on{display:block}
</style>
