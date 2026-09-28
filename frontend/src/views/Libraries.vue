<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { libsApi, libTypesApi } from '../api'
import { naturalDesc } from '../utils/naturalSort'
import BuildTag from '../components/BuildTag.vue'

/* 一级素材库：后端 library 表动态加载（不再写死四类），素材库页显示全部（含停用） */
const libTypes = ref([])
const curLib = ref(null)             /* 当前库 id（number） */
const curGroup = ref('all')          /* 'all' = 全部组 */
const groupsByLib = reactive({})     /* 库 id → 组列表 */
const images = ref([])
const loading = ref(false)

const curLibDef = computed(() => libTypes.value.find(l => l.id === curLib.value))
const curGroups = computed(() => groupsByLib[curLib.value] || [])
const allCount = computed(() => curGroups.value.reduce((a, g) => a + (g.image_count || 0), 0))
const libCount = lib => (groupsByLib[lib.id] || []).reduce((a, g) => a + (g.image_count || 0), 0)

function errMsg(e) {
  const d = e?.response?.data?.detail
  return typeof d === 'string' ? d : (e?.message || '未知错误')
}
function asList(data) {
  return Array.isArray(data) ? data : (data?.items || [])
}

async function loadLibTypes() {
  const { data } = await libTypesApi.list()
  libTypes.value = asList(data)
}

async function loadGroups(libId) {
  try {
    const { data } = await libsApi.groups(libId)
    groupsByLib[libId] = asList(data)
  } catch (e) {
    groupsByLib[libId] = []
    ElMessage.error('加载组列表失败：' + errMsg(e))
  }
}

async function loadImages() {
  if (curLib.value == null) { images.value = []; return }
  loading.value = true
  try {
    const params = curGroup.value === 'all' ? {} : { group_id: curGroup.value }
    const { data } = await libsApi.images(curLib.value, params)
    /* 后端按 id 升序返回；前端按名称自然排序倒序展示（8-10 排在 8-2 前） */
    images.value = asList(data).sort((a, b) => naturalDesc(a.original_name, b.original_name))
  } catch (e) {
    images.value = []
    ElMessage.error('加载图片失败：' + errMsg(e))
  } finally {
    loading.value = false
  }
}

async function refresh() {
  await loadGroups(curLib.value)
  await loadImages()
}

function onTabChange() {
  curGroup.value = 'all'
  refresh()
}
function switchTab(l) {
  if (curLib.value === l.id) return
  curLib.value = l.id
  onTabChange()
}
function pickGroup(gid) {
  curGroup.value = gid
  loadImages()
}

/* ── 一级库管理（新建/改名/换色/排序/启停/删库） ── */
const manageDialog = ref(false)

function openManage() {
  manageDialog.value = true
}
async function reloadLibTypes(keepId) {
  await loadLibTypes()
  if (keepId != null && libTypes.value.some(l => l.id === keepId)) curLib.value = keepId
  else {
    curLib.value = libTypes.value[0]?.id ?? null
    curGroup.value = 'all'
    if (curLib.value != null) await loadGroups(curLib.value)
  }
}
async function createLib() {
  let name
  try {
    ({ value: name } = await ElMessageBox.prompt('新素材库名称（将出现在工作台与素材库 tab）：', '新建素材库', {
      confirmButtonText: '创建', cancelButtonText: '取消',
      inputPattern: /\S/, inputErrorMessage: '名称不能为空',
    }))
  } catch { return }
  try {
    const { data } = await libTypesApi.create({ name: name.trim() })
    ElMessage.success(`已创建素材库「${data.name}」，默认启用`)
    await reloadLibTypes(data.id)
  } catch (e) { ElMessage.error('创建失败：' + errMsg(e)) }
}
async function renameLib(l) {
  let name
  try {
    ({ value: name } = await ElMessageBox.prompt(`把库「${l.name}」改名为：`, '库改名', {
      confirmButtonText: '保存', cancelButtonText: '取消',
      inputValue: l.name, inputPattern: /\S/, inputErrorMessage: '名称不能为空',
    }))
  } catch { return }
  try {
    await libTypesApi.update(l.id, { name: name.trim() })
    ElMessage.success('库已改名')
    await loadLibTypes()
  } catch (e) { ElMessage.error('改名失败：' + errMsg(e)) }
}
async function recolorLib(l, ev) {
  try {
    await libTypesApi.update(l.id, { color: ev.target.value })
    await loadLibTypes()
  } catch (e) { ElMessage.error('换色失败：' + errMsg(e)) }
}
async function toggleLib(l) {
  try {
    await libTypesApi.update(l.id, { enabled: !l.enabled })
    ElMessage.success(l.enabled ? `已停用「${l.name}」，工作台不再显示（素材仍可上传管理）`
                                : `已启用「${l.name}」，工作台恢复显示`)
    await loadLibTypes()
  } catch (e) { ElMessage.error('操作失败：' + errMsg(e)) }
}
async function moveLib(l, dir) {
  const idx = libTypes.value.findIndex(x => x.id === l.id)
  const other = libTypes.value[idx + dir]
  if (!other) return
  try {
    await Promise.all([
      libTypesApi.update(l.id, { sort_order: other.sort_order }),
      libTypesApi.update(other.id, { sort_order: l.sort_order }),
    ])
    await loadLibTypes()
  } catch (e) { ElMessage.error('排序失败：' + errMsg(e)) }
}
async function deleteLib(l) {
  try {
    await ElMessageBox.confirm(
      `确定删除素材库「${l.name}」？仅允许删除空库；若有组会被拒绝。`,
      '删除素材库',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch { return }
  try {
    await libTypesApi.remove(l.id)
    ElMessage.success(`已删除素材库「${l.name}」`)
    await reloadLibTypes(null)
  } catch (e) { ElMessage.error('删除失败：' + errMsg(e)) }
}

/* ── 组管理 ── */
async function createGroup() {
  let name
  try {
    ({ value: name } = await ElMessageBox.prompt('新组名称（=款式 / 文件夹名）：', '新建组', {
      confirmButtonText: '创建', cancelButtonText: '取消',
      inputPattern: /\S/, inputErrorMessage: '名称不能为空',
    }))
  } catch { return } /* 取消 / 关闭 */
  try {
    await libsApi.createGroup(curLib.value, name.trim())
    ElMessage.success(`已创建组「${name.trim()}」`)
    await refresh()
  } catch (e) { ElMessage.error('创建组失败：' + errMsg(e)) }
}

async function renameGroup(g) {
  let name
  try {
    ({ value: name } = await ElMessageBox.prompt(`把组「${g.name}」改名为：`, '组改名', {
      confirmButtonText: '保存', cancelButtonText: '取消',
      inputValue: g.name, inputPattern: /\S/, inputErrorMessage: '名称不能为空',
    }))
  } catch { return } /* 取消 / 关闭 */
  try {
    await libsApi.renameGroup(curLib.value, g.id, name.trim())
    ElMessage.success('组已改名')
    await refresh()
  } catch (e) { ElMessage.error('组改名失败：' + errMsg(e)) }
}

async function deleteGroup(g) {
  try {
    await ElMessageBox.confirm(
      `删除组会同时删除组内全部图片记录与磁盘文件，不可恢复。确定删除「${g.name}」？`,
      '删除组',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch { return }
  try {
    await libsApi.deleteGroup(curLib.value, g.id)
    if (curGroup.value === g.id) curGroup.value = 'all'
    ElMessage.success(`已删除组「${g.name}」`)
    await refresh()
  } catch (e) { ElMessage.error('删除组失败：' + errMsg(e)) }
}

/* ── 图片瓦片操作 ── */
async function renameImage(img) {
  let name
  try {
    ({ value: name } = await ElMessageBox.prompt(`把「${img.original_name}」改名为：`, '图片改名', {
      confirmButtonText: '保存', cancelButtonText: '取消',
      inputValue: img.original_name, inputPattern: /\S/, inputErrorMessage: '名称不能为空',
    }))
  } catch { return } /* 取消 / 关闭 */
  try {
    await libsApi.updateImage(curLib.value, img.id, { original_name: name.trim() })
    ElMessage.success('已改名')
    await loadImages()
  } catch (e) { ElMessage.error('改名失败：' + errMsg(e)) }
}

/* 移动到其他组 */
const moveDialog = ref(false)
const moveImg = ref(null)
const moveTarget = ref(null)
const moveOptions = computed(() =>
  moveImg.value ? curGroups.value.filter(g => g.id !== moveImg.value.group_id) : [])

function openMove(img) {
  if (!moveOptions.value.length) { ElMessage.warning('这个库没有其他组可移动，先新建一个组'); return }
  moveImg.value = img
  moveTarget.value = moveOptions.value[0]?.id ?? null
  moveDialog.value = true
}
async function doMove() {
  const img = moveImg.value
  const gid = moveTarget.value
  const g = curGroups.value.find(x => x.id === gid)
  moveDialog.value = false
  try {
    await libsApi.updateImage(curLib.value, img.id, { group_id: gid })
    ElMessage.success(`已移动到「${g ? g.name : '目标组'}」`)
    await refresh()
  } catch (e) { ElMessage.error('移动失败：' + errMsg(e)) }
}

async function removeImage(img) {
  try {
    await ElMessageBox.confirm(
      `确定删除「${img.original_name}」？磁盘文件将一并删除。`,
      '删除图片',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch { return }
  try {
    await libsApi.deleteImage(curLib.value, img.id)
    ElMessage.success('已删除（磁盘文件一并删除）')
    await refresh()
  } catch (e) { ElMessage.error('删除失败：' + errMsg(e)) }
}

/* ── 大图预览：点瓦片图片区放大，Esc / 点遮罩关闭 ── */
const previewUrl = ref('')
function openPreview(img) {
  previewUrl.value = img.url
}

/* ── 上传（multipart 字段 files，group_id 为 form 字段）── */
const fileInput = ref(null)
const uploading = ref(false)
const uploadDialog = ref(false)
const uploadGroupId = ref(null)

function triggerUpload() {
  if (curLib.value == null) { ElMessage.warning('请先在「管理库」里新建一个素材库'); return }
  if (curGroup.value !== 'all') { fileInput.value?.click(); return }
  if (!curGroups.value.length) { ElMessage.warning('请先新建一个组，再上传图片'); return }
  if (!uploadGroupId.value || !curGroups.value.some(g => g.id === uploadGroupId.value)) {
    uploadGroupId.value = (curGroup.value !== 'all' && curGroup.value) || curGroups.value[0]?.id || null
  }
  uploadDialog.value = true
}
function confirmUploadGroup() {
  if (!uploadGroupId.value) { ElMessage.warning('请选择上传到的组'); return }
  uploadDialog.value = false
  fileInput.value?.click()
}
async function onFileChange(e) {
  const files = Array.from(e.target.files || [])
  e.target.value = ''
  if (!files.length) return
  const gid = curGroup.value !== 'all' ? curGroup.value : uploadGroupId.value
  uploading.value = true
  try {
    const { data } = await libsApi.upload(curLib.value, gid, files)
    /* 按 后端实际结果 组装：全部成功 / 有跳过（附原因摘要） */
    const reasons = (data.errors || []).join('；')
    if (data.skipped > 0) {
      ElMessage.warning(`已上传 ${data.imported} 张，跳过 ${data.skipped} 张：${reasons}`)
    } else {
      ElMessage.success(`已上传 ${data.imported} 张`)
    }
    await refresh()
  } catch (err) {
    ElMessage.error('上传失败：' + errMsg(err))
  } finally {
    uploading.value = false
  }
}

/* ── 导入磁盘目录 ── */
const importDialog = ref(false)
const importPath = ref('')
const importing = ref(false)
const importStat = ref(null)

function openImport() {
  importStat.value = null
  importPath.value = ''
  importDialog.value = true
}
async function runImport() {
  const dir = importPath.value.trim()
  if (!dir) { ElMessage.warning('请填写后端机器上的绝对路径'); return }
  importing.value = true
  try {
    const { data } = await libsApi.importDir(curLib.value, dir)
    importStat.value = data
    ElMessage.success(`导入完成：导入 ${data.images_imported} 张`)
    await refresh()
  } catch (e) {
    ElMessage.error('导入失败：' + errMsg(e))
  } finally {
    importing.value = false
  }
}

onMounted(async () => {
  await loadLibTypes()
  curLib.value = libTypes.value[0]?.id ?? null
  await Promise.all(libTypes.value.map(l => loadGroups(l.id)))
  await loadImages()
})
</script>

<template>
  <div class="view libs-view">
    <div class="view-head">
      <h1>素材库</h1><span class="sub">一级 = 素材库（可自建/启停），二级 = 组（款式 / 文件夹）</span>
      <div class="right">
        <BuildTag />
        <button class="btn" @click="openManage">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/></svg>管理库
        </button>
        <button class="btn" @click="openImport">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/></svg>导入磁盘目录
        </button>
        <button class="btn primary" :disabled="uploading" @click="triggerUpload">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 16V4M6 10l6-6 6 6M4 20h16"/></svg>上传图片
        </button>
      </div>
    </div>

    <!-- 一级库 tab：自定义胶囊（统一内距/圆点/计数，停用的库灰显：仍可上传管理，工作台不显示） -->
    <div class="libtabs">
      <button v-for="l in libTypes" :key="l.id" type="button" class="libtab"
              :class="{ on: curLib === l.id, off: !l.enabled }"
              :title="l.enabled ? '' : '未启用：工作台不显示，仍可上传管理'"
              @click="switchTab(l)">
        <span class="ld" :style="{ background: l.color || 'var(--ink-3)' }"></span>
        <span class="lt">{{ l.name }}库</span>
        <span class="cnt num">{{ libCount(l) }}</span>
      </button>
    </div>

    <div class="lib-wrap" v-if="curLib != null">
      <!-- 左：组列表 -->
      <div class="card lib-groups">
        <div class="add-wrap"><button class="btn sm add-btn" @click="createGroup">＋ 新建组</button></div>
        <div class="glist">
          <button class="pg-item" :class="{ on: curGroup === 'all' }" @click="pickGroup('all')">
            <span class="gname">全部组</span><span class="n num">{{ allCount }}</span>
          </button>
          <div v-for="g in curGroups" :key="g.id" class="pg-item has-ops" :class="{ on: curGroup === g.id }" @click="pickGroup(g.id)">
            <span class="gname">{{ g.name }}</span>
            <span class="gops">
              <button title="改名" @click.stop="renameGroup(g)"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 20l4-1L20 7l-3-3L5 16z"/></svg></button>
              <button title="删除组" @click.stop="deleteGroup(g)"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13"/></svg></button>
            </span>
            <span class="n num">{{ g.image_count }}</span>
          </div>
        </div>
      </div>

      <!-- 右：图片网格 -->
      <div class="card lib-gridwrap">
        <div class="lib-grid" v-loading="loading">
          <template v-if="images.length">
            <div v-for="img in images" :key="img.id" class="gtile">
              <!-- 图片区：完整缩放（contain 留白），点击放大；操作按钮悬浮其上 -->
              <div class="thumb" title="点击放大预览" @click="openPreview(img)">
                <img :src="img.url" :alt="img.original_name" loading="lazy">
                <div class="ops" @click.stop>
                  <button title="改名" @click="renameImage(img)"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 20l4-1L20 7l-3-3L5 16z"/></svg></button>
                  <button title="移动到其他组" @click="openMove(img)"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M5 9h10l-3-3M19 15H9l3 3"/></svg></button>
                  <button title="删除" @click="removeImage(img)"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13"/></svg></button>
                </div>
              </div>
              <!-- 名称行：瓦片下方独立一行，不叠在图上，行高随内容撑开 -->
              <span class="name" :title="`${img.original_name} · ${img.group_name}`">{{ img.original_name }} · {{ img.group_name }}</span>
            </div>
          </template>
          <div v-else-if="!loading" class="empty">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><rect x="3" y="4" width="18" height="16" rx="2.5"/><path d="M3.5 17.5l5-4.5 4 3.5 3.5-3 4.5 4"/></svg>
            <b>{{ curGroup === 'all' ? '这个库还没有图片' : '这个组还是空的' }}</b>
            <p>单张上传，或用右上角「导入磁盘目录」把现有文件夹整组搬进来（一级子文件夹 = 组）。</p>
            <button class="btn sm primary" @click="openImport">去导入</button>
          </div>
        </div>
      </div>
    </div>

    <div class="lib-wrap" v-else>
      <div class="card" style="grid-column:1/-1;padding:40px;text-align:center;color:var(--ink-3)">
        还没有任何素材库，点右上角「管理库」新建一个。
      </div>
    </div>

    <!-- 隐藏的多选文件输入 -->
    <input ref="fileInput" type="file" multiple accept=".png,.jpg,.jpeg,.webp" class="hidden-file" @change="onFileChange">

    <!-- 一级库管理 -->
    <el-dialog v-model="manageDialog" title="管理素材库" width="560px" align-center>
      <div class="mgmt-body">
        <div class="mgmt-tip">启用的库出现在工作台参考图选择里；停用的库仅在这里可见，仍可上传管理。排序即 tab 顺序。</div>
        <div class="mgmt-row mgmt-head">
          <span class="c">色</span><span class="n">名称</span><span class="g">组数</span><span class="e">启用</span><span class="o">操作</span>
        </div>
        <div v-for="(l, i) in libTypes" :key="l.id" class="mgmt-row">
          <label class="c" title="点击换色">
            <span class="dot" :style="{ background: l.color || 'var(--ink-3)' }"></span>
            <input type="color" class="color-input" :value="l.color?.startsWith('#') ? l.color : '#888888'"
                   @change="recolorLib(l, $event)">
          </label>
          <span class="n" :class="{ off: !l.enabled }">{{ l.name }}</span>
          <span class="g num">{{ l.group_count }}</span>
          <span class="e"><el-switch :model-value="l.enabled" @change="toggleLib(l)" /></span>
          <span class="o">
            <button class="btn sm" :disabled="i === 0" title="上移" @click="moveLib(l, -1)">↑</button>
            <button class="btn sm" :disabled="i === libTypes.length - 1" title="下移" @click="moveLib(l, 1)">↓</button>
            <button class="btn sm" @click="renameLib(l)">改名</button>
            <button class="btn sm danger" @click="deleteLib(l)">删除</button>
          </span>
        </div>
        <button class="btn sm add-lib" @click="createLib">＋ 新建素材库</button>
      </div>
      <template #footer>
        <div class="dlg-foot">
          <button class="btn primary" @click="manageDialog = false">完成</button>
        </div>
      </template>
    </el-dialog>

    <!-- 上传位置选择（当前处于「全部组」时） -->
    <el-dialog v-model="uploadDialog" title="上传图片" width="380px" align-center>
      <label class="field"><span>上传到的组</span>
        <el-select v-model="uploadGroupId" placeholder="选择组" style="width:100%">
          <el-option v-for="g in curGroups" :key="g.id" :value="g.id" :label="g.name" />
        </el-select>
      </label>
      <template #footer>
        <div class="dlg-foot">
          <button class="btn" @click="uploadDialog = false">取消</button>
          <button class="btn primary" @click="confirmUploadGroup">选择文件</button>
        </div>
      </template>
    </el-dialog>

    <!-- 移动到其他组 -->
    <el-dialog v-model="moveDialog" :title="`移动「${moveImg?.original_name}」`" width="380px" align-center>
      <label class="field"><span>目标组</span>
        <el-select v-model="moveTarget" placeholder="选择组" style="width:100%">
          <el-option v-for="g in moveOptions" :key="g.id" :value="g.id" :label="g.name" />
        </el-select>
      </label>
      <template #footer>
        <div class="dlg-foot">
          <button class="btn" @click="moveDialog = false">取消</button>
          <button class="btn primary" @click="doMove">移动</button>
        </div>
      </template>
    </el-dialog>

    <!-- 导入磁盘目录 -->
    <el-dialog v-model="importDialog" title="从磁盘导入素材" width="460px" align-center>
      <div class="imp-body">
        <label class="field"><span>后端机器上的绝对路径</span>
          <input class="input num imp-path" v-model="importPath" placeholder="D:\素材库\袜子">
        </label>
        <p class="imp-tip">一级子文件夹会变成「组」，组内图片递归导入；已存在的同名组直接并入。类型支持 png / jpg / webp，单张不超过 20MB。</p>
        <div v-if="importStat" class="imp-stat">
          导入完成：<b>{{ importStat.groups_created }}</b> 个新组 · 并入 <b>{{ importStat.groups_merged }}</b> 个同名组 ·
          导入 <b>{{ importStat.images_imported }}</b> 张 · 跳过 <b>{{ importStat.skipped }}</b> 张
        </div>
      </div>
      <template #footer>
        <div class="dlg-foot">
          <button class="btn" @click="importDialog = false">取消</button>
          <button class="btn primary" :disabled="importing" @click="runImport">{{ importing ? '扫描中…' : '开始导入' }}</button>
        </div>
      </template>
    </el-dialog>

    <!-- 大图预览（teleport 到 body，层级高于页面） -->
    <el-image-viewer
      v-if="previewUrl"
      :url-list="[previewUrl]"
      teleported
      hide-on-click-modal
      @close="previewUrl = ''"
    />
  </div>
</template>

<style scoped>
.view{flex:1;min-height:0;display:flex;flex-direction:column}

/* 一级库 tab：自定义胶囊按钮（统一内距/圆点/计数间距，激活态只换底色和描边） */
.libtabs{flex:none;display:flex;flex-wrap:wrap;gap:8px;padding:12px 22px 0}
.libtab{display:inline-flex;align-items:center;gap:7px;height:34px;padding:0 14px;border:1px solid transparent;border-radius:11px;background:none;font-family:inherit;font-size:13px;font-weight:600;color:var(--ink-3);cursor:pointer;transition:background .15s ease,border-color .15s ease,color .15s ease}
.libtab:hover{color:var(--ink-1)}
.libtab.on{background:var(--panel-2);border-color:var(--border);color:var(--ink-1)}
.libtab.off{opacity:.45}
.libtab .ld{width:8px;height:8px;border-radius:50%;flex:none}
.libtab .lt{white-space:nowrap}
.libtab .cnt{font-size:11px;color:var(--ink-3)}

/* 布局：220px 组列 | 1fr 网格 */
.lib-wrap{flex:1;min-height:0;display:grid;grid-template-columns:220px minmax(0,1fr);gap:14px;padding:14px 22px 20px}
.lib-groups{overflow-y:auto;padding:10px}
.add-wrap{padding-bottom:8px}
.add-btn{width:100%}
.glist{display:flex;flex-direction:column}
.pg-item{position:relative;width:100%;text-align:left;padding:8px 11px;border-radius:11px;font-size:13px;color:var(--ink-2);display:flex;align-items:center;gap:8px;margin-bottom:2px;cursor:pointer;border:0;background:none;font-family:inherit}
.pg-item:hover{background:var(--panel-2)}
.pg-item.on{background:var(--panel-2);color:var(--ink-1);font-weight:600}
.pg-item .gname{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pg-item .n{font-size:11px;color:var(--ink-3);flex:none}
.pg-item .gops{display:none;gap:2px;flex:none}
.pg-item:hover .gops{display:flex}
.pg-item.has-ops:hover .n{display:none}
.gops button{width:20px;height:20px;border-radius:6px;display:grid;place-items:center;color:var(--ink-3);border:0;background:none;cursor:pointer}
.gops button:hover{background:var(--panel-3);color:var(--ink-1)}

/* 图片网格：瓦片 = 正方形图区（contain 完整缩放，允许留白）+ 下方独立名称行；
 * 行高由内容自然撑开，名称不再绝对定位叠在图上，杜绝行间压盖 */
.lib-gridwrap{display:flex;flex-direction:column;min-height:0;overflow:hidden}
.lib-grid{flex:1;min-height:0;overflow-y:auto;padding:14px;display:grid;grid-template-columns:repeat(auto-fill,132px);grid-auto-rows:max-content;gap:12px;align-items:start;align-content:start}
.gtile{display:flex;flex-direction:column;width:100%;min-width:0;border-radius:11px;overflow:hidden;border:1px solid var(--border);background:var(--panel-2)}
.gtile .thumb{position:relative;height:132px;width:100%;cursor:zoom-in}
.gtile .thumb img{width:100%;height:100%;object-fit:contain;display:block}
.gtile .ops{position:absolute;top:6px;right:6px;display:none;gap:4px;z-index:2}
.gtile .thumb:hover .ops{display:flex}
.gtile .ops button{width:24px;height:24px;border-radius:7px;background:var(--img-chip-bg);color:var(--ink-2);display:grid;place-items:center;border:1px solid var(--border-2);cursor:pointer}
.gtile .ops button:hover{color:var(--ink-1)}
.gtile .name{flex:none;font-size:11px;padding:5px 8px;color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;border-top:1px solid var(--border)}
.hidden-file{display:none}

/* 库管理弹窗 */
.mgmt-tip{font-size:12px;color:var(--ink-3);line-height:1.7;margin-bottom:12px}
.mgmt-row{display:flex;align-items:center;gap:10px;padding:7px 4px;border-bottom:1px solid var(--border)}
.mgmt-row.mgmt-head{font-size:11px;color:var(--ink-3);border-bottom:1px solid var(--border-2)}
.mgmt-row .c{width:26px;flex:none;display:grid;place-items:center}
.mgmt-row .n{flex:1;min-width:0;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mgmt-row .n.off{color:var(--ink-3);text-decoration:line-through}
.mgmt-row .g{width:44px;flex:none;font-size:12px;color:var(--ink-3)}
.mgmt-row .e{width:44px;flex:none}
.mgmt-row .o{flex:none;display:flex;gap:4px}
.mgmt-row .o .btn{padding:3px 8px;font-size:11px}
.mgmt-row .o .btn.danger:hover{color:var(--down);border-color:var(--down)}
.mgmt-row .dot{width:14px;height:14px;border-radius:50%;display:block;cursor:pointer}
.mgmt-row .color-input{width:0;height:0;opacity:0;padding:0;border:0}
.mgmt-row .c:hover .dot{outline:2px solid var(--border-2);cursor:pointer}
.add-lib{margin-top:12px;width:100%}

/* 弹窗公共 */
.dlg-foot{display:flex;gap:8px;justify-content:flex-end}
.imp-body{display:flex;flex-direction:column}
.imp-path{font-family:var(--mono)}
.imp-tip{font-size:12px;color:var(--ink-3);line-height:1.7;margin:4px 0 0}
.imp-stat{margin-top:10px;font-size:12.5px;color:var(--ink-2);background:var(--panel-2);border-radius:11px;padding:9px 12px}
.imp-stat b{color:var(--up)}
</style>
