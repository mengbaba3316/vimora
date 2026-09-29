<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { promptsApi } from '../api'
import { store } from '../store'
import PaletteButton from '../components/PaletteButton.vue'

const router = useRouter()

/* ── 列表 + 搜索（300ms 防抖走服务端 keyword 过滤）── */
const list = ref([])
const total = ref(0)
const loading = ref(false)
const keyword = ref('')

let searchTimer = null
function onSearchInput() {
  page.value = 1
  clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 300)
}

function errMsg(e) {
  const d = e?.response?.data?.detail
  return typeof d === 'string' ? d : (e?.message || '未知错误')
}

const page = ref(1)
const pageSize = 50
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

function gotoPage(p) {
  const next = Math.min(pageCount.value, Math.max(1, p))
  if (next === page.value) return
  page.value = next
  load()
}

async function load() {
  loading.value = true
  try {
    const { data } = await promptsApi.list({
      keyword: keyword.value.trim() || undefined,
      page: page.value, size: pageSize,
    })
    list.value = data.items || []
    total.value = data.total ?? list.value.length
  } catch (e) {
    list.value = []
    total.value = 0
    ElMessage.error('加载提示词失败：' + errMsg(e))
  } finally {
    loading.value = false
  }
}

/* ── 抽屉表单：新建 / 编辑 ── */
const drawer = ref(false)
const saving = ref(false)
const editId = ref(null)
const form = ref({ name: '', tags: '', content: '', remark: '' })

function openCreate() {
  editId.value = null
  form.value = { name: '', tags: '', content: '', remark: '' }
  drawer.value = true
}
function openEdit(row) {
  editId.value = row.id
  form.value = { name: row.name, tags: row.tags || '', content: row.content || '', remark: row.remark || '' }
  drawer.value = true
}

async function save() {
  const f = form.value
  if (!f.name.trim() || !f.content.trim()) { ElMessage.warning('名称和内容必填'); return }
  saving.value = true
  try {
    const payload = { name: f.name.trim(), tags: f.tags.trim(), content: f.content, remark: f.remark.trim() }
    if (editId.value) {
      await promptsApi.update(editId.value, payload)
      ElMessage.success('已保存')
    } else {
      await promptsApi.create(payload)
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

async function remove() {
  try {
    await ElMessageBox.confirm(
      `删除后历史任务仍使用当时的快照，不受影响。确定删除「${form.value.name}」？`,
      '删除提示词',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch { return }
  try {
    await promptsApi.remove(editId.value)
    ElMessage.success('已删除（历史任务不受影响）')
    drawer.value = false
    await load()
  } catch (e) {
    ElMessage.error('删除失败：' + errMsg(e))
  }
}

/* ── 用起来：挂到全局 store 后跳工作台 ── */
function use(row) {
  store.pendingPrompt = { id: row.id, name: row.name, content: row.content }
  router.push('/')
  ElMessage.success('已加载到工作台，可自由修改（不回写库）')
}

/* 内容摘要：首行截 64 字 */
function summary(content) {
  return (content || '').split('\n')[0].slice(0, 64) + '…'
}
function tagList(tags) {
  return (tags || '').split(',').map(t => t.trim()).filter(Boolean)
}

onMounted(load)
</script>

<template>
  <div class="view">
    <div class="view-head">
      <h1>提示词库</h1><span class="sub">沉淀可复用的生图提示词，名称会用作输出目录名</span>
      <div class="right">
        <PaletteButton />
        <button class="btn primary" @click="openCreate">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>新建提示词
        </button>
      </div>
    </div>
    <div class="view-body">
      <div class="toolbar">
        <input class="input grow" v-model="keyword" placeholder="搜索名称、内容、标签…" @input="onSearchInput">
        <span class="chip mute num">{{ total }} 条</span>
      </div>
      <div class="card table-card" v-loading="loading">
        <table>
          <thead>
            <tr>
              <th style="width:180px">名称</th>
              <th>内容摘要</th>
              <th style="width:180px">标签</th>
              <th style="width:160px">更新时间</th>
              <th style="width:130px"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in list" :key="p.id">
              <td><span class="name">{{ p.name }}</span></td>
              <td><span class="digest">{{ summary(p.content) }}</span></td>
              <td>
                <el-tag v-for="t in tagList(p.tags)" :key="t" type="info" effect="plain" size="small" class="ptag">{{ t }}</el-tag>
              </td>
              <td class="mono-cell">{{ p.updated_at }}</td>
              <td>
                <div class="ops-cell">
                  <button class="btn sm" @click="openEdit(p)">编辑</button>
                  <button class="btn sm" @click="use(p)">用起来</button>
                </div>
              </td>
            </tr>
            <tr v-if="!list.length && !loading">
              <td colspan="5">
                <div class="empty"><b>没有匹配的提示词</b><p>换个关键词，或新建一条。</p></div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="ppager num" v-if="total > 0">
        <span>共 {{ total }} 条 · 第 {{ page }}/{{ pageCount }} 页</span>
        <span class="pager-ops">
          <button class="btn sm" :disabled="page <= 1" @click="gotoPage(page - 1)">上一页</button>
          <button class="btn sm" :disabled="page >= pageCount" @click="gotoPage(page + 1)">下一页</button>
        </span>
      </div>
    </div>

    <el-drawer v-model="drawer" size="560px" :title="editId ? `编辑「${form.name}」` : '新建提示词'">
      <div class="drawer-body">
        <label class="field"><span>名称 <i class="req">*</i>（同时用作输出目录名）</span>
          <input class="input" v-model="form.name" placeholder="如：街拍白裙">
        </label>
        <label class="field"><span>标签（逗号分隔）</span>
          <input class="input" v-model="form.tags" placeholder="街拍,白裙">
        </label>
        <label class="field"><span>提示词内容 <i class="req">*</i></span>
          <textarea class="textarea pf-content" v-model="form.content" rows="12"></textarea>
        </label>
        <label class="field"><span>备注</span>
          <input class="input" v-model="form.remark" placeholder="给未来的自己看的使用说明">
        </label>
      </div>
      <template #footer>
        <div class="drawer-foot">
          <button v-if="editId" class="btn danger" @click="remove">删除</button>
          <button class="btn cancel" @click="drawer = false">取消</button>
          <button class="btn primary" :disabled="saving" @click="save">保存</button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.view{flex:1;min-height:0;display:flex;flex-direction:column}
.digest{font-size:12.5px;color:var(--ink-3)}
.mono-cell{font-family:var(--mono);font-size:12px}
.ptag{margin-right:4px}
.drawer-body{padding:0 4px}
.pf-content{font-family:var(--mono);font-size:12.5px;line-height:1.7}
.drawer-foot{display:flex;gap:8px;width:100%}
.drawer-foot .cancel{margin-left:auto}

/* 提示词翻页器 */
.ppager{display:flex;align-items:center;justify-content:space-between;margin-top:12px;font-size:12px;color:var(--ink-3)}
.ppager .pager-ops{display:flex;gap:8px}
</style>
