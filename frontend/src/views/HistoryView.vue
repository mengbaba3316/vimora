<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { tasksApi, libTypesApi } from '../api'
import { useTaskPolling } from '../composables/useTaskPolling'
import PaletteButton from '../components/PaletteButton.vue'

/*
 * 历史任务页（原型 #view-history + #taskDrawer）：
 * 筛选（状态/关键字）+ 列表 + 轮询（queued/running 时每 2 秒静默刷新）
 * + 详情抽屉（失败原文 / 部分成功警示 / 参数快照 / 提示词与参考图快照 / 结果图 / 重跑 / 删除）。
 * 状态五值：queued 灰 / running 黑·心跳 / success 绿 / partial 琥珀 / failed 红。
 */

/* 一级库定义：详情快照按 library id（旧任务为 face 等字符串 key）显示库名与色点 */
const libTypes = ref([])

const STATUS_META = {
  queued:  { label: '排队中',   cls: 'st-queued' },
  running: { label: '生成中',   cls: 'st-running' },
  success: { label: '成功',     cls: 'st-success' },
  partial: { label: '部分成功', cls: 'st-partial' },
  failed:  { label: '失败',     cls: 'st-failed' },
}
/* 后端 status 权威只有 pending/running/success/failed（规格 §4 DDL），五态展示在前端派生：
   pending → queued；success 且成功张数 < n → partial；否则原值。
   成功张数优先取后端 ok 字段（若将来提供），当前按 images 数计算。 */
function normStatus(t) {
  const s = t?.status
  if (s === 'pending') return 'queued'
  if (s === 'success' && (t.ok ?? okCount(t)) < t.n) return 'partial'
  return s || 'queued'
}
function stMeta(t) { return STATUS_META[normStatus(t)] || STATUS_META.queued }

function errMsg(e) {
  const d = e?.response?.data?.detail
  return typeof d === 'string' ? d : (e?.message || '未知错误')
}

/* ── 列表 + 筛选 + 分页 ── */
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 50
const loading = ref(false)
const filterStatus = ref('')
const filterKw = ref('')

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

async function refresh(silent = true) {
  if (!silent) loading.value = true
  try {
    /* 筛选映射：后端 status 只有 pending/running/success/failed（§4 DDL 权威）。
       「排队中」→ 请求 status=pending；「部分成功」→ 请求 status=success 后
       客户端按 ok<n 过滤（partial 是派生态，后端无法直接查询）；其余直传。 */
    const fs = filterStatus.value
    const { data } = await tasksApi.list({
      status: fs === 'queued' ? 'pending' : (fs === 'partial' ? 'success' : fs),
      keyword: filterKw.value.trim(),
      page: page.value,
      size: pageSize,
    })
    let items = data.items || []
    let count = data.total || 0
    if (fs === 'partial') {
      items = items.filter(t => normStatus(t) === 'partial')
      count = items.length   /* success 总数含全部成功会虚高，展示客户端过滤后的条数 */
    }
    list.value = items
    total.value = count
    /* 抽屉开着时用列表里的最新数据同步详情（轮询带来的状态流转立即可见） */
    if (drawer.value && detail.value) {
      const fresh = list.value.find(x => x.id === detail.value.id)
      if (fresh) detail.value = fresh
    }
  } catch (e) {
    if (!silent) ElMessage.error('加载历史任务失败：' + errMsg(e))
  } finally {
    if (!silent) loading.value = false
  }
}

function onStatusChange() {
  page.value = 1
  refresh(false)
}

let kwTimer = null
let skipKwWatch = false
watch(filterKw, () => {
  if (skipKwWatch) { skipKwWatch = false; return }
  clearTimeout(kwTimer)
  kwTimer = setTimeout(() => { page.value = 1; refresh(false) }, 300)   /* 关键字防抖 300ms */
})

function clearFilters() {
  skipKwWatch = true
  filterStatus.value = ''
  filterKw.value = ''
  clearTimeout(kwTimer)
  page.value = 1
  refresh(false)
}

function goto(p) {
  const next = Math.min(pageCount.value, Math.max(1, p))
  if (next === page.value) return
  page.value = next
  refresh(false)
}

/* ── 轮询：列表存在 queued/running 时每 2 秒静默刷新 ── */
const hasActive = () =>
  list.value.some(t => ['queued', 'running', 'pending'].includes(t.status))
useTaskPolling(refresh, hasActive)

/* 初始加载（轮询的即时 tick 只在已有 queued/running 时触发，空列表时靠这里） */
onMounted(async () => {
  refresh(false)
  try {
    const { data } = await libTypesApi.list()
    libTypes.value = Array.isArray(data) ? data : (data?.items || [])
  } catch { /* 库名显示退化为快照原始值 */ }
})

function okCount(t) { return t.images?.length || 0 }

/* ── 详情抽屉 ── */
const router = useRouter()
const drawer = ref(false)
const detail = ref(null)

async function openDetail(t) {
  detail.value = t
  drawer.value = true
  try {
    const { data } = await tasksApi.detail(t.id)
    if (drawer.value && detail.value?.id === data.id) detail.value = data
  } catch { /* 拉不到详情就按列表行数据展示 */ }
}

/* 参考图快照：assets 按库分组（色点 + 数量 + 迷你缩略）。
   快照结构只有 image_ids（§4.1）；若条目带 file_path(s)/images 则用
   /files/libraries/<file_path> 出缩略图，否则色块占位。 */
function entryThumbs(a) {
  if (Array.isArray(a.images) && a.images.length) {
    return a.images.map(im => typeof im === 'string'
      ? { path: im } : { path: im.file_path || '', name: im.original_name || '' })
  }
  if (Array.isArray(a.file_paths) && a.file_paths.length) {
    return a.file_paths.map(p => ({ path: p }))
  }
  return (a.image_ids || []).map(id => ({ path: '', name: `#${id}` }))
}

const assetGroups = computed(() => {
  const order = []
  const map = new Map()
  for (const a of detail.value?.assets || []) {
    const thumbs = entryThumbs(a)
    if (!thumbs.length) continue
    if (!map.has(a.library)) {
      const meta = libTypes.value.find(l => l.id === a.library || l.key === a.library)
        || { id: a.library, name: a.library_name || a.library, color: 'var(--ink-3)' }
      const g = { ...meta, count: 0, minis: [] }
      map.set(a.library, g)
      order.push(g)
    }
    const g = map.get(a.library)
    g.count += thumbs.length
    g.minis.push(...thumbs)
  }
  return order
})

function miniSrc(m) { return m.path ? `/files/libraries/${m.path}` : '' }

/* 结果图：/files/outputs/<file_path>，点击 el-image 看大图，悬停出下载 */
const resImages = computed(() => (detail.value?.images || []).map(im => ({
  ...im,
  src: im.url || `/files/outputs/${im.file_path}`,
})))
const resTitle = computed(() => {
  const d = detail.value
  if (!resImages.value.length) return '结果图'
  return d?.output_dir ? `结果图 · 归档于 outputs/${d.output_dir}/` : '结果图'
})
const resHint = computed(() => {
  const s = normStatus(detail.value)
  if (s === 'failed') return '无输出，磁盘未产生文件。'
  if (s === 'queued' || s === 'running') return '任务完成后这里会显示结果图。'
  return '无输出，磁盘未产生文件。'
})

const resSnapshot = computed(() => {
  const d = detail.value
  if (!d) return []
  const rows = [
    { k: '源站', v: d.provider_name || '—', mono: false },
    { k: '发送方式', v: d.endpoint || '—', mono: true },
    { k: '模型 / 尺寸', v: `${d.model || '—'} · ${d.size || '—'}`, mono: true },
  ]
  const res = d.extra?.resolution
  if (res) rows.push({ k: '清晰度', v: res, mono: true })
  rows.push({
    k: '结果',
    v: `${okCount(d)}/${d.n} 张 · 状态 ${stMeta(d).label}`,
    mono: false,
  })
  return rows
})

/* ── 重跑 / 删除 / 复制错误 ── */
const rerunning = reactive({})

async function rerun(t) {
  if (rerunning[t.id]) return
  rerunning[t.id] = true
  try {
    const { data } = await tasksApi.rerun(t.id)
    drawer.value = false
    ElMessage.success(`任务 #${data.id} 已加入队列（参数快照一致），去工作台可继续提交新任务`)
    router.push('/')
  } catch (e) {
    ElMessage.error('重跑失败：' + errMsg(e))
  } finally {
    rerunning[t.id] = false
  }
}

async function removeRecord() {
  const t = detail.value
  if (!t) return
  try {
    await ElMessageBox.confirm(
      `删除任务 #${t.id}「${t.prompt_name}」的历史记录？磁盘文件保留，已生成的图片不受影响。`,
      '删除记录',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch { return /* 用户取消 */ }
  try {
    await tasksApi.remove(t.id)
    ElMessage.success('已删除记录（磁盘文件保留）')
    drawer.value = false
    await refresh(false)
  } catch (e) {
    ElMessage.error('删除失败：' + errMsg(e))
  }
}

async function copyError() {
  const text = detail.value?.error_message || ''
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('错误信息已复制')
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    ta.remove()
    ElMessage.success('错误信息已复制')
  }
}
</script>

<template>
  <div class="view">
    <div class="view-head">
      <h1>历史任务</h1><span class="sub">每次运行按「提示词名 / 时间戳」归档，参数快照可回看可重跑</span>
      <div class="right">
        <PaletteButton />
        <span class="chip mute"><span class="d live-dot"></span>排队 / 生成中的任务每 2 秒自动刷新状态</span>
      </div>
    </div>

    <div class="view-body">
      <div class="toolbar">
        <el-select id="hisStatus" v-model="filterStatus" class="wselect" style="width:130px" @change="onStatusChange">
          <el-option value="" label="全部状态" />
          <el-option value="queued" label="排队中" />
          <el-option value="running" label="生成中" />
          <el-option value="success" label="成功" />
          <el-option value="partial" label="部分成功" />
          <el-option value="failed" label="失败" />
        </el-select>
        <input id="hisSearch" v-model="filterKw" class="input grow" placeholder="搜索提示词名 / 内容…">
        <span id="hisTotal" class="chip mute num">{{ total }} 条</span>
      </div>

      <div class="card table-card" v-loading="loading">
        <table>
          <thead>
            <tr>
              <th style="width:150px">创建时间</th>
              <th style="width:170px">提示词</th>
              <th style="width:110px">源站</th>
              <th style="width:90px">方式</th>
              <th class="num" style="width:110px">结果</th>
              <th style="width:110px">状态</th>
              <th style="width:140px"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in list" :key="t.id">
              <td class="mono-cell">{{ t.created_at || '—' }}</td>
              <td><span class="name">#{{ t.id }} {{ t.prompt_name }}</span></td>
              <td>{{ t.provider_name }}</td>
              <td><span class="chip mute num">{{ t.endpoint }}</span></td>
              <td class="num">{{ okCount(t) }}/{{ t.n }} 张</td>
              <td>
                <span class="chip" :class="stMeta(t).cls">
                  <span class="d"></span>{{ stMeta(t).label }}
                </span>
              </td>
              <td>
                <div class="ops-cell">
                  <button class="btn sm" @click="openDetail(t)">详情</button>
                  <button class="btn sm" :disabled="rerunning[t.id]" @click="rerun(t)">重跑</button>
                </div>
              </td>
            </tr>
            <tr v-if="!list.length && !loading">
              <td colspan="7">
                <div class="empty">
                  <template v-if="filterStatus || filterKw">
                    <b>没有匹配的任务</b>
                    <p>换个筛选条件，或清除状态过滤。</p>
                    <button class="btn sm" @click="clearFilters">清除筛选</button>
                  </template>
                  <template v-else>
                    <b>还没有任务</b>
                    <p>去工作台提交第一个生图任务，这里会按时间归档每次运行。</p>
                  </template>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="pager">
        <span class="num">共 {{ total }} 条 · 第 {{ page }}/{{ pageCount }} 页</span>
        <span class="pager-ops">
          <button class="btn sm" :disabled="page <= 1" @click="goto(page - 1)">上一页</button>
          <button class="btn sm" :disabled="page >= pageCount" @click="goto(page + 1)">下一页</button>
        </span>
      </div>
    </div>

    <!-- 抽屉：任务详情（原型 #taskDrawer / #tdBody） -->
    <el-drawer v-model="drawer" size="760px" class="task-drawer">
      <template #header>
        <div class="td-h">
          <b v-if="detail">任务 #{{ detail.id }} · {{ detail.prompt_name }}</b>
          <span class="sub num">{{ detail?.created_at }}</span>
        </div>
      </template>

      <div v-if="detail" class="td-body">
        <!-- 失败：错误原文默认展开 + 底部复制按钮 -->
        <div v-if="detail.error_message" class="errbox">
          <h5>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h.01"/></svg>
            失败原因（原文）
          </h5>
          <pre>{{ detail.error_message }}</pre>
        </div>

        <!-- 部分成功：警示条（partial 由 success + ok<n 派生，见 normStatus） -->
        <div v-if="normStatus(detail) === 'partial'" class="warnbox">
          <span>⚠ {{ okCount(detail) }}/{{ detail.n }} 张成功</span>
        </div>

        <!-- 参数快照网格 -->
        <div class="snap-grid">
          <div v-for="r in resSnapshot" :key="r.k" class="snap">
            <div class="k">{{ r.k }}</div>
            <div class="v" :class="{ mono: r.mono }">{{ r.v }}</div>
          </div>
        </div>

        <!-- 提示词快照 -->
        <div class="sec-t">提示词快照</div>
        <div class="prompt-snap">{{ detail.prompt_content }}</div>

        <!-- 参考图快照（按库分组） -->
        <div class="sec-t">参考图快照</div>
        <template v-if="assetGroups.length">
          <div v-for="g in assetGroups" :key="g.id" class="asset-row">
            <span class="ld" :style="{ background: g.color }"></span>
            {{ g.name }}库<b style="margin-left:2px">× {{ g.count }}</b>
            <span class="mini">
              <template v-for="(m, i) in g.minis" :key="i">
                <img v-if="miniSrc(m)" :src="miniSrc(m)" :alt="m.name || '参考图'" loading="lazy">
                <i v-else :style="{ background: `linear-gradient(135deg, ${g.color}, transparent 140%), var(--panel-2)` }"></i>
              </template>
            </span>
          </div>
        </template>
        <div v-else class="asset-row muted">纯文生图，未选参考图</div>

        <!-- 结果图网格 -->
        <div class="sec-t">{{ resTitle }}</div>
        <div v-if="resImages.length" class="res-grid">
          <div v-for="r in resImages" :key="r.id" class="res-tile">
            <el-image :src="r.src" fit="cover" :preview-src-list="resImages.map(x => x.src)"
                      :initial-index="resImages.indexOf(r)" preview-teleported hide-on-click-modal />
            <a class="dl" :href="r.src" download>下载</a>
          </div>
        </div>
        <p v-else class="res-none">{{ resHint }}</p>
      </div>

      <template #footer>
        <div class="td-foot">
          <button class="btn danger td-del" @click="removeRecord">删除记录</button>
          <span class="td-foot-right">
            <button v-if="detail?.error_message" class="btn" @click="copyError">复制错误信息</button>
            <button class="btn primary" :disabled="!detail || rerunning[detail.id]" @click="rerun(detail)">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12a9 9 0 11-2.6-6.4M21 4v5h-5"/></svg>
              用同样配置重跑
            </button>
          </span>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style>
/* 抽屉壳对齐原型 .drawer-h/.drawer-b/.drawer-f（drawer teleport 到 body，须用全局作用域） */
.task-drawer .el-drawer__header{padding:15px 18px;margin-bottom:0;border-bottom:1px solid var(--border);color:var(--ink-1)}
.task-drawer .el-drawer__body{padding:16px 18px}
.task-drawer .el-drawer__footer{padding:13px 18px;border-top:1px solid var(--border)}
</style>

<style scoped>
.view{flex:1;min-height:0;display:flex;flex-direction:column}

/* 头部轮询提示 chip 的绿点（原型 .chip .d[style=background:var(--up)]） */
.live-dot{background:var(--up)}

/* 状态五值 chip（原型 .chip.st-*），running 带心跳点 */
.chip.st-queued{background:var(--panel-2);color:var(--ink-3);border:1px solid var(--border)}
.chip.st-running{background:var(--accent-soft);color:var(--accent)}
.chip.st-success{background:var(--up-soft);color:var(--up)}
.chip.st-failed{background:var(--down-soft);color:var(--down)}
.chip.st-partial{background:var(--warn-soft);color:var(--warn)}
.chip.st-running .d{animation:dot-pulse 1.6s ease-in-out infinite}
@keyframes dot-pulse{0%,100%{opacity:1}50%{opacity:.25}}

.mono-cell{font-family:var(--mono);font-size:12px}

/* 分页（原型 .pager） */
.pager{display:flex;align-items:center;justify-content:space-between;margin-top:12px;font-size:12px;color:var(--ink-3)}
.pager-ops{display:flex;gap:8px}

/* ── 抽屉内（原型 #tdBody 各区块）── */
.td-h{display:flex;align-items:baseline;gap:10px;min-width:0}
.td-h b{font-size:14.5px}
.td-h .sub{font-size:12px;color:var(--ink-3)}
.td-body{padding:0}
.td-foot{display:flex;align-items:center;gap:8px;width:100%}
.td-del{margin-right:auto}
.td-foot-right{display:flex;gap:8px}

.errbox{background:var(--down-soft);border:1px solid var(--down-line);border-radius:8px;padding:11px 13px;margin-bottom:14px}
.errbox h5{font-size:12px;color:var(--down);margin:0 0 5px;display:flex;align-items:center;gap:6px}
.errbox pre{font-family:var(--mono);font-size:11.5px;color:var(--ink-2);white-space:pre-wrap;word-break:break-all;max-height:120px;overflow-y:auto;margin:0}

.warnbox{background:var(--warn-soft);border:1px solid var(--warn-line);border-radius:8px;padding:11px 13px;margin-bottom:14px;font-size:12.5px;color:var(--warn);display:flex;gap:8px;align-items:center;justify-content:space-between}

.snap-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px}
.snap{background:var(--panel-2);border-radius:8px;padding:9px 12px}
.snap .k{font-size:11px;color:var(--ink-3)}
.snap .v{font-size:13px;font-weight:600;margin-top:1px;word-break:break-all}
.snap .v.mono{font-family:var(--mono);font-weight:500;font-size:12px}

.sec-t{font-size:11px;letter-spacing:.1em;color:var(--ink-3);font-weight:700;margin:16px 0 8px}
.prompt-snap{background:var(--page);border:1px solid var(--border);border-radius:8px;padding:11px 13px;font-family:var(--mono);font-size:12px;line-height:1.7;color:var(--ink-2);max-height:150px;overflow-y:auto;white-space:pre-wrap;word-break:break-all}

.asset-row{display:flex;align-items:center;gap:8px;padding:6px 0;font-size:12.5px;color:var(--ink-2)}
.asset-row .ld{width:8px;height:8px;border-radius:50%;flex:none}
.asset-row.muted{color:var(--ink-3)}
.asset-row .mini{display:flex;gap:4px;margin-left:6px}
.asset-row .mini img,.asset-row .mini i{width:22px;height:22px;border-radius:6px;display:block;border:1px solid var(--border);object-fit:cover}

.res-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:10px}
.res-tile{aspect-ratio:1;border-radius:8px;overflow:hidden;position:relative;border:1px solid var(--border)}
.res-tile:hover{border-color:var(--accent)}
.res-tile .el-image{width:100%;height:100%;display:block;cursor:zoom-in}
.res-tile .el-image img{width:100%;height:100%;object-fit:cover}
.res-tile .dl{position:absolute;right:6px;bottom:6px;opacity:0;background:var(--img-chip-bg);border-radius:7px;padding:4px 8px;font-size:11px;color:var(--ink-1);border:1px solid var(--border-2);text-decoration:none;transition:opacity .12s ease}
.res-tile:hover .dl{opacity:1}
.res-none{font-size:12.5px;color:var(--ink-3);margin:0}
</style>
