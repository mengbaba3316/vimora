<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { libsApi } from '../api'
import { L } from '../i18n'

/*
 * 素材选择抽屉（分页版）：左侧组筛选，右侧图片网格按页加载。
 * 每页张数按抽屉网格实际尺寸动态计算（分辨率自适应），无滚动条。
 * 用法（工作台）：
 *   <AssetPicker ref="x" :library="id" :lib-name="名" :lib-color="色" v-model="sel" />
 *   x.value.open()
 * 确定 → emit('update:modelValue', 有序 image_id 数组)；取消 / 关闭不改值。
 * 跨页点选：draft 按 id 维护，翻页不影响已选与顺序。
 */
const props = defineProps({
  library: { type: [String, Number], required: true },  /* 一级素材库 id */
  libName: { type: String, default: '素材' },            /* 抽屉标题显示用 */
  libColor: { type: String, default: 'var(--ink-3)' },
  modelValue: { type: Array, default: () => [] },       /* 有序 image_id 数组 */
})
const emit = defineEmits(['update:modelValue'])

const drawer = ref(false)
const loading = ref(false)
const groups = ref([])
const images = ref([])
const curGroup = ref('all')   /* 'all' = 全部组 */
const draft = ref([])         /* 点选顺序维护的已选 id */

/* 分页：每页张数按网格实际尺寸动态计算 */
const page = ref(1)
const size = ref(12)
const imgTotal = ref(0)
const gridEl = ref(null)
let obs = null

const libMeta = computed(() => ({ name: props.libName, color: props.libColor }))
const subText = computed(() => `已选 ${draft.value.length} 张，按点选顺序传给接口`)
const pageCount = computed(() => Math.max(1, Math.ceil(imgTotal.value / size.value)))
const allCount = computed(() => groups.value.reduce((a, g) => a + (g.image_count || 0), 0))

function errMsg(e) {
  const d = e?.response?.data?.detail
  return typeof d === 'string' ? d : (e?.message || '未知错误')
}
function asList(data) {
  return Array.isArray(data) ? data : (data?.items || [])
}

/* 测量网格：算列数与行高（CSS 变量下发，瓦片拉伸撑满无滚动条） */
function measure() {
  const el = gridEl.value
  if (!el || !el.clientHeight) return
  const pager = el.querySelector('.ppager')
  const pagerH = (pager ? pager.offsetHeight : 30) + 10          /* 翻页器实高 + 间距 */
  const w = el.clientWidth - 28, h = el.clientHeight - 28 - pagerH   /* 内边距 14×2 + 翻页器 */
  const cols = Math.max(2, Math.floor((w + 10) / 142))           /* 132px 最小瓦片 + 10px 间距 */
  let rows = Math.max(1, Math.floor((h + 10) / 169))             /* 瓦片高 ≈ 159 + 间距 */
  while (rows > 1 && (h - (rows - 1) * 10) / rows < 130) rows--
  const rowH = Math.floor((h - (rows - 1) * 10) / rows)
  el.style.setProperty('--cols', cols)
  el.style.setProperty('--rowh', rowH + 'px')
  const s = cols * rows
  if (s && s !== size.value) { size.value = s; page.value = 1 }
}
/* 渲染后自检：内容溢出就压行高（rounding/字体差异兜底） */
function fitRows() {
  const el = gridEl.value, pg = el?.querySelector('.pgrid')
  if (!el || !pg) return
  let guard = 6
  while (pg.scrollHeight > pg.clientHeight + 2 && guard--) {
    const cur = parseInt(el.style.getPropertyValue('--rowh')) || 160
    if (cur <= 120) break
    el.style.setProperty('--rowh', (cur - 12) + 'px')
  }
}

function ensureObs() {
  if (!obs && gridEl.value) {
    obs = new ResizeObserver(() => measure())
    obs.observe(gridEl.value)
  }
}
onBeforeUnmount(() => obs?.disconnect())

async function load() {
  loading.value = true
  try {
    await nextTick()
    ensureObs()
    measure()
    setTimeout(measure, 380)   /* 抽屉展开动画结束后再校一次（动画中 clientHeight=0 会被跳过） */
    const params = curGroup.value === 'all'
      ? { page: page.value, size: size.value }
      : { group_id: curGroup.value, page: page.value, size: size.value }
    const [g, imgs] = await Promise.all([
      libsApi.groups(props.library),
      libsApi.images(props.library, params),
    ])
    groups.value = asList(g.data)
    imgTotal.value = imgs.data.total ?? 0
    /* 后端已按名称自然倒排（全局有序），此处不再排序 */
    images.value = asList(imgs.data.items)
    await nextTick()
    fitRows()
  } catch (e) {
    groups.value = []
    images.value = []
    ElMessage.error('加载素材失败：' + errMsg(e))
  } finally {
    loading.value = false
  }
}

function gotoPage(p) {
  const next = Math.min(pageCount.value, Math.max(1, p))
  if (next === page.value) return
  page.value = next
  load()
}

watch(curGroup, () => { page.value = 1; load() })
watch(() => props.library, () => { page.value = 1 })

/* 打开：草稿 = 外部值，回到第 1 页加载（组列表全量、图片分页） */
async function open() {
  draft.value = [...(props.modelValue || [])]
  curGroup.value = 'all'
  page.value = 1
  drawer.value = true
  await load()
}

function groupName(img) {
  if (img.group_name) return img.group_name
  return groups.value.find(g => g.id === img.group_id)?.name || ''
}
/* 瓦片序号：点选顺序（从 1 起），未选中返回 0 */
function ordOf(id) {
  return draft.value.indexOf(id) + 1
}

function toggleTile(img) {
  const i = draft.value.indexOf(img.id)
  if (i > -1) draft.value.splice(i, 1)
  else draft.value.push(img.id)
}

/* ── 放大镜预览：右上角小按钮打开大图查看器，不影响点选 ── */
const previewUrl = ref('')
/* 预览地址与列表一致：静态文件挂载 /files/libraries/<file_path> */
function openPreview(img) {
  previewUrl.value = img.file_path ? `/files/libraries/${img.file_path}` : (img.url || '')
}

function clearLib() {
  draft.value = []
}

function confirm() {
  emit('update:modelValue', [...draft.value])
  drawer.value = false
}

defineExpose({ open })
</script>

<template>
  <el-drawer v-model="drawer" size="640px" class="picker-drawer">
    <template #header>
      <div class="picker-h">
        <span class="ld" :style="{ background: libMeta.color }"></span>
        <b>{{ L('选择{name}参考图', { name: libMeta.name }) }}</b>
        <span class="sub">{{ subText }}</span>
      </div>
    </template>

    <div class="picker-body" v-loading="loading">
      <!-- 左：组列表（含「全部组」与图片计数） -->
      <div class="picker-groups">
        <button class="pg-item" :class="{ on: curGroup === 'all' }" @click="curGroup = 'all'">
          <span class="gname">{{ L('全部组') }}</span><span class="n num">{{ allCount }}</span>
        </button>
        <button v-for="g in groups" :key="g.id" class="pg-item" :class="{ on: curGroup === g.id }" @click="curGroup = g.id">
          <span class="gname">{{ g.name }}</span><span class="n num">{{ g.image_count }}</span>
        </button>
      </div>

      <!-- 右：图片网格（分页）+ 底部翻页器 -->
      <div class="picker-grid" ref="gridEl">
        <div class="pgrid" v-loading="loading">
          <template v-if="images.length">
            <div v-for="img in images" :key="img.id" class="ptile" :class="{ on: ordOf(img.id) > 0 }" @click="toggleTile(img)">
              <div class="thumb">
                <img :src="img.url" :alt="img.original_name" loading="lazy">
                <button class="zoom" title="放大预览" @click.stop="openPreview(img)">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.8-3.8"/></svg>
                </button>
              </div>
              <span class="tick">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>
              </span>
              <span class="ord num">{{ ordOf(img.id) }}</span>
              <span class="name" :title="`${img.original_name}${groupName(img) ? ` · ${groupName(img)}` : ''}`">{{ img.original_name }}{{ groupName(img) ? ` · ${groupName(img)}` : '' }}</span>
            </div>
          </template>
          <div v-else-if="!loading" class="empty">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><rect x="3" y="4" width="18" height="16" rx="2.5"/><path d="M3.5 17.5l5-4.5 4 3.5 3.5-3 4.5 4"/></svg>
            <b>{{ curGroup === 'all' ? '这个库还是空的' : '这个组还是空的' }}</b>
            <p>去「素材库」上传图片，或用「导入磁盘目录」把已有文件夹整组搬进来。</p>
          </div>
        </div>
        <div class="ppager num">
          <button class="btn sm" :disabled="page <= 1" @click="gotoPage(page - 1)">{{ L('上一页') }}</button>
          <span>{{ L('第 {p}/{c} 页 · 共 {n} 张', { p: page, c: pageCount, n: imgTotal }) }}</span>
          <button class="btn sm" :disabled="page >= pageCount" @click="gotoPage(page + 1)">{{ L('下一页') }}</button>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="picker-foot">
        <button class="btn" @click="clearLib">{{ L('清空该库') }}</button>
        <button class="btn primary" @click="confirm">{{ L('确定') }}</button>
      </div>
    </template>
  </el-drawer>

  <!-- 大图预览（teleport 到 body） -->
  <el-image-viewer
    v-if="previewUrl"
    :url-list="[previewUrl]"
    teleported
    hide-on-click-modal
    @close="previewUrl = ''"
  />
</template>

<style>
/* 抽屉壳对齐原型 .drawer-h/.drawer-b/.drawer-f（drawer teleport 到 body，须用全局作用域） */
.picker-drawer .el-drawer__header{padding:15px 18px;margin-bottom:0;border-bottom:1px solid var(--border);color:var(--ink-1)}
.picker-drawer .el-drawer__body{padding:0;overflow:hidden}
.picker-drawer .el-drawer__footer{padding:13px 18px;border-top:1px solid var(--border)}
.picker-h{display:flex;align-items:center;gap:10px;min-width:0}
.picker-h .ld{width:9px;height:9px;border-radius:50%;flex:none}
.picker-h b{font-size:14.5px}
.picker-h .sub{font-size:12px;color:var(--ink-3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* 168px 组列 | 1fr 网格（原型 .picker-body） */
.picker-body{display:grid;grid-template-columns:168px minmax(0,1fr);gap:0;height:100%;min-height:0}
.picker-groups{border-right:1px solid var(--border);overflow-y:auto;padding:10px}
.pg-item{position:relative;width:100%;text-align:left;padding:8px 11px;border-radius:11px;font-size:13px;color:var(--ink-2);display:flex;align-items:center;gap:8px;margin-bottom:2px;cursor:pointer;border:0;background:none;font-family:inherit}
.pg-item:hover{background:var(--panel-2)}
.pg-item.on{background:color-mix(in srgb,var(--accent) 16%,var(--panel-2));color:var(--accent);font-weight:600}
.pg-item.on .n{color:var(--accent)}
.pg-item .gname{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pg-item .n{margin-left:auto;font-family:var(--mono);font-size:11px;color:var(--ink-3);flex:none}

/* 右侧：网格（瓦片拉伸撑满）+ 底部翻页器，无滚动条 */
.picker-grid{overflow:hidden;padding:14px;display:flex;flex-direction:column;gap:10px;min-height:0}
.pgrid{flex:1;min-height:0;overflow:hidden;display:grid;grid-template-columns:repeat(var(--cols,3),1fr);grid-auto-rows:var(--rowh,160px);gap:10px;align-items:stretch}
.ptile{position:relative;display:flex;flex-direction:column;width:100%;min-width:0;border-radius:11px;overflow:hidden;cursor:pointer;border:1.5px solid var(--border);background:var(--panel-2);transition:border-color .12s ease,transform .12s ease}
.ptile:hover{transform:translateY(-2px)}
.ptile .thumb{position:relative;flex:1;min-height:0;width:100%}
.ptile .thumb img{width:100%;height:100%;object-fit:contain;display:block}
.ptile .zoom{position:absolute;top:6px;right:6px;width:24px;height:24px;padding:0;border-radius:7px;background:var(--img-chip-bg);color:var(--ink-2);display:grid;place-items:center;border:1px solid var(--border-2);cursor:zoom-in;opacity:0;pointer-events:none;transition:opacity .12s ease;z-index:2}
.ptile:hover .zoom{opacity:1;pointer-events:auto}
.ptile .zoom:hover{color:var(--ink-1)}
.ptile .name{flex:none;font-size:10.5px;padding:4px 8px;color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;border-top:1px solid var(--border)}
.ptile .tick{position:absolute;top:7px;left:7px;width:20px;height:20px;border-radius:50%;background:var(--img-chip-bg-soft);border:1.5px solid var(--border-2);display:grid;place-items:center;color:transparent}
.ptile.on{border-color:var(--accent)}
.ptile.on .tick{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
.ptile .ord{position:absolute;top:7px;right:7px;min-width:17px;height:17px;padding:0 4px;border-radius:99px;background:var(--accent);color:var(--on-accent);font-size:10px;font-weight:700;display:none;place-items:center;font-family:var(--mono)}
.ppager{display:flex;align-items:center;justify-content:center;gap:12px;flex:none;font-size:11px;color:var(--ink-3)}

.picker-foot{display:flex;gap:8px;justify-content:flex-end;width:100%}
</style>
