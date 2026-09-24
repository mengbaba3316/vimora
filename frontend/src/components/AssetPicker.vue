<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { libsApi } from '../api'
import { naturalDesc } from '../utils/naturalSort'

/*
 * 四库通用素材选择抽屉。
 * 用法（工作台）：
 *   <AssetPicker ref="facePicker" library="face" v-model="sel.face" />
 *   facePicker.value.open()
 * 确定 → emit('update:modelValue', 有序 image_id 数组)；取消 / 关闭不改值。
 */
const props = defineProps({
  library: { type: String, required: true },          /* face / outfit / socks / pose */
  modelValue: { type: Array, default: () => [] },     /* 有序 image_id 数组 */
})
const emit = defineEmits(['update:modelValue'])

const LIBS = [
  { id: 'face',   name: '人脸', color: 'var(--lib-face)' },
  { id: 'outfit', name: '服装', color: 'var(--lib-outfit)' },
  { id: 'socks',  name: '袜子', color: 'var(--lib-socks)' },
  { id: 'pose',   name: '姿势', color: 'var(--lib-pose)' },
]

const drawer = ref(false)
const loading = ref(false)
const groups = ref([])
const images = ref([])
const curGroup = ref('all')   /* 'all' = 全部组 */
const draft = ref([])         /* 点选顺序维护的已选 id */

const libMeta = computed(() => LIBS.find(l => l.id === props.library) || { name: '素材', color: 'var(--ink-3)' })
const subText = computed(() => `已选 ${draft.value.length} 张，按点选顺序传给接口`)

function errMsg(e) {
  const d = e?.response?.data?.detail
  return typeof d === 'string' ? d : (e?.message || '未知错误')
}
function asList(data) {
  return Array.isArray(data) ? data : (data?.items || [])
}

/* 打开：草稿 = 外部值，并行拉组列表与全量图片（组过滤在本地做） */
async function open() {
  draft.value = [...(props.modelValue || [])]
  curGroup.value = 'all'
  drawer.value = true
  loading.value = true
  try {
    const [g, imgs] = await Promise.all([libsApi.groups(props.library), libsApi.images(props.library)])
    groups.value = asList(g.data)
    /* 后端按 id 升序返回；前端按名称自然排序倒序展示（8-10 排在 8-2 前） */
    images.value = asList(imgs.data).sort((a, b) => naturalDesc(a.original_name, b.original_name))
  } catch (e) {
    groups.value = []
    images.value = []
    ElMessage.error('加载素材失败：' + errMsg(e))
  } finally {
    loading.value = false
  }
}

const allCount = computed(() => images.value.length)
const shownImages = computed(() =>
  curGroup.value === 'all' ? images.value : images.value.filter(i => i.group_id === curGroup.value))

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
        <b>选择{{ libMeta.name }}参考图</b>
        <span class="sub">{{ subText }}</span>
      </div>
    </template>

    <div class="picker-body" v-loading="loading">
      <!-- 左：组列表（含「全部组」与图片计数） -->
      <div class="picker-groups">
        <button class="pg-item" :class="{ on: curGroup === 'all' }" @click="curGroup = 'all'">
          <span class="gname">全部组</span><span class="n num">{{ allCount }}</span>
        </button>
        <button v-for="g in groups" :key="g.id" class="pg-item" :class="{ on: curGroup === g.id }" @click="curGroup = g.id">
          <span class="gname">{{ g.name }}</span><span class="n num">{{ g.image_count }}</span>
        </button>
      </div>

      <!-- 右：图片网格，点选切换 + 顺序徽标；右上角放大镜只管预览 -->
      <div class="picker-grid">
        <template v-if="shownImages.length">
          <div v-for="img in shownImages" :key="img.id" class="ptile" :class="{ on: ordOf(img.id) > 0 }" @click="toggleTile(img)">
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
    </div>

    <template #footer>
      <div class="picker-foot">
        <button class="btn" @click="clearLib">清空该库</button>
        <button class="btn primary" @click="confirm">确定</button>
      </div>
    </template>
  </el-drawer>

  <!-- 大图预览（teleport 到 body，层级高于抽屉）；Esc / 点遮罩关闭 -->
  <el-image-viewer
    v-if="previewUrl"
    :url-list="[previewUrl]"
    teleported
    hide-on-click-modal
    @close="previewUrl = ''"
  />
</template>

<style>
/* 抽屉壳对齐原型 .drawer-h/.drawer-f（drawer teleport 到 body，须用全局作用域） */
.picker-drawer .el-drawer__header{padding:15px 18px;margin-bottom:0;border-bottom:1px solid var(--border);color:var(--ink-1)}
.picker-drawer .el-drawer__body{padding:0;overflow:hidden}
.picker-drawer .el-drawer__footer{padding:13px 18px;border-top:1px solid var(--border)}
</style>

<style scoped>

.picker-h{display:flex;align-items:center;gap:10px;min-width:0}
.picker-h .ld{width:9px;height:9px;border-radius:50%;flex:none}
.picker-h b{font-size:14.5px}
.picker-h .sub{font-size:12px;color:var(--ink-3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* 168px 组列 | 1fr 网格（原型 .picker-body） */
.picker-body{display:grid;grid-template-columns:168px minmax(0,1fr);gap:0;height:100%;min-height:0}
.picker-groups{border-right:1px solid var(--border);overflow-y:auto;padding:10px}
.pg-item{position:relative;width:100%;text-align:left;padding:8px 11px;border-radius:11px;font-size:13px;color:var(--ink-2);display:flex;align-items:center;gap:8px;margin-bottom:2px;cursor:pointer;border:0;background:none;font-family:inherit}
.pg-item:hover{background:var(--panel-2)}
.pg-item.on{background:var(--panel-2);color:var(--ink-1);font-weight:600}
.pg-item .gname{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pg-item .n{margin-left:auto;font-family:var(--mono);font-size:11px;color:var(--ink-3);flex:none}

.picker-grid{overflow-y:auto;padding:14px;display:grid;grid-template-columns:repeat(auto-fill,132px);grid-auto-rows:max-content;gap:10px;align-items:start;align-content:start}
/* 瓦片 = 正方形图区（contain 完整缩放，允许留白）+ 下方独立名称行；行高随内容撑开，不压盖 */
.ptile{position:relative;display:flex;flex-direction:column;width:100%;min-width:0;border-radius:11px;overflow:hidden;cursor:pointer;border:1.5px solid var(--border);background:var(--panel-2);transition:border-color .12s ease,transform .12s ease}
.ptile:hover{transform:translateY(-2px)}
.ptile .thumb{position:relative;height:132px;width:100%}
.ptile .thumb img{width:100%;height:100%;object-fit:contain;display:block}
.ptile .zoom{position:absolute;top:6px;right:6px;width:24px;height:24px;padding:0;border-radius:7px;background:var(--img-chip-bg);color:var(--ink-2);display:grid;place-items:center;border:1px solid var(--border-2);cursor:zoom-in;opacity:0;pointer-events:none;transition:opacity .12s ease;z-index:2}
.ptile:hover .zoom{opacity:1;pointer-events:auto}
.ptile .zoom:hover{color:var(--ink-1)}
.ptile.on .zoom{top:29px}   /* 右上角被选中序号徽标占用时，放大镜下移避让 */
.ptile .name{flex:none;font-size:10.5px;padding:4px 8px;color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;border-top:1px solid var(--border)}
.ptile .tick{position:absolute;top:7px;left:7px;width:20px;height:20px;border-radius:50%;background:var(--img-chip-bg-soft);border:1.5px solid var(--border-2);display:grid;place-items:center;color:transparent}
.ptile.on{border-color:var(--accent)}
.ptile.on .tick{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
.ptile .ord{position:absolute;top:7px;right:7px;min-width:17px;height:17px;padding:0 4px;border-radius:99px;background:var(--accent);color:var(--on-accent);font-size:10px;font-weight:700;display:none;place-items:center;font-family:var(--mono)}
.ptile.on .ord{display:grid}

.picker-foot{display:flex;gap:8px;justify-content:flex-end;width:100%}
</style>
