<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { promptsApi } from '../api'
import { useFindReplace } from '../composables/useFindReplace'

/*
 * 提示词编辑器（原型 .col-prompt 的 findbar + textarea + prompt-foot）。
 * props.modelValue 双向绑定提示词全文；props.prompt 为当前选中的库内提示词
 * （{id,name,tags,remark}，可为 null=未选）。
 * 「保存回提示词库」PUT 当前 prompt.id；未选时弹名称另存。
 * 另存成功后 emit('saved', 新提示词)，由工作台刷新列表并选中。
 */
const props = defineProps({
  modelValue: { type: String, default: '' },
  prompt: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'saved'])

/* 内部 text 同步外部 modelValue：替换/重扫读本地值，避免等 props 回流的时序问题 */
const text = ref(props.modelValue)
watch(() => props.modelValue, (v) => { if (v !== text.value) text.value = v })
watch(text, (v) => emit('update:modelValue', v))

const editorEl = ref(null)
const {
  query: findQuery, replaceWith: replaceText,
  label: findLabel, rescan, jump, replaceOne, replaceAll,
} = useFindReplace(text)

const noneResult = computed(() => !!findQuery.value && !findLabel.value.includes('/'))
const charCount = computed(() => text.value.length.toLocaleString() + ' 字')

function onFindInput() { rescan() }
function onFindKeydown(e) {
  if (e.key === 'Enter') { e.preventDefault(); jump(e.shiftKey ? -1 : 1, editorEl) }
}
/* 模板内联表达式会解包顶层 ref，jump 需要 ref 本身，故经此中转 */
function jumpPrev() { jump(-1, editorEl) }
function jumpNext() { jump(1, editorEl) }
function onReplaceOne() { replaceOne() }
function onReplaceAll() {
  if (!findQuery.value) return
  const q = findQuery.value
  const n = replaceAll()
  ElMessage.success(n ? `已替换 ${n} 处「${q}」` : '没有可替换的内容')
}

/* 提示词切换（外部换内容）时清空查找状态 */
function resetFind() {
  findQuery.value = ''
  replaceText.value = ''
  rescan()
}
defineExpose({ resetFind })

function errMsg(e) {
  const d = e?.response?.data?.detail
  return typeof d === 'string' ? d : (e?.message || '未知错误')
}

/* 另存为新提示词：弹名称（默认原名-变体）→ POST → emit saved */
async function saveAsNew() {
  let name
  try {
    const r = await ElMessageBox.prompt('给这份内容起个名称（同时用作输出目录名）：', '另存为新提示词', {
      inputValue: (props.prompt?.name || '未命名') + '-变体',
      inputPattern: /\S/,
      inputErrorMessage: '名称必填',
      confirmButtonText: '保存',
      cancelButtonText: '取消',
    })
    name = r.value.trim()
  } catch { return /* 取消 */ }
  try {
    const { data } = await promptsApi.create({ name, tags: '变体', content: text.value, remark: '' })
    ElMessage.success(`已另存为「${name}」`)
    emit('saved', data)
  } catch (e) {
    ElMessage.error('另存失败：' + errMsg(e))
  }
}

/* 保存回提示词库：PUT 当前 prompt_id；未选时弹名称另存 */
async function saveBack() {
  if (!props.prompt?.id) { saveAsNew(); return }
  try {
    await promptsApi.update(props.prompt.id, {
      name: props.prompt.name,
      tags: props.prompt.tags || '',
      content: text.value,
      remark: props.prompt.remark || '',
    })
    ElMessage.success(`已保存回「${props.prompt.name}」`)
  } catch (e) {
    ElMessage.error('保存失败：' + errMsg(e))
  }
}
</script>

<template>
  <div class="findbar">
    <div class="row">
      <span class="lbl">查找</span>
      <input id="findInput" v-model="findQuery" placeholder="在提示词内容内查找，如 场景 / white dress"
             @input="onFindInput" @keydown="onFindKeydown">
      <button id="findPrev" class="iconbtn" title="上一个" @click="jumpPrev">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 14l6-6 6 6"/></svg>
      </button>
      <button id="findNext" class="iconbtn" title="下一个" @click="jumpNext">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 10l6 6 6-6"/></svg>
      </button>
      <span id="findCount" class="fcount num" :class="{ none: noneResult }">{{ findLabel }}</span>
    </div>
    <div class="row">
      <span class="lbl">替换</span>
      <input id="replaceInput" v-model="replaceText" placeholder="替换为…">
      <button id="repOne" class="btn sm" @click="onReplaceOne">替换</button>
      <button id="repAll" class="btn sm" @click="onReplaceAll">全部替换</button>
    </div>
  </div>
  <div class="prompt-editor">
    <textarea id="promptText" ref="editorEl" v-model="text" spellcheck="false"></textarea>
  </div>
  <div class="prompt-foot">
    <span id="charCount" class="wc num">{{ charCount }}</span>
    <button id="saveAsNew" class="btn sm" @click="saveAsNew">另存为新提示词</button>
    <button id="saveBack" class="btn sm primary" @click="saveBack">保存回提示词库</button>
  </div>
</template>

<style scoped>
/* 对照原型 .findbar / .prompt-editor / .prompt-foot */
.findbar{margin:10px 16px 0;background:var(--panel-2);border:1px solid var(--border);border-radius:11px;padding:8px 10px;display:flex;flex-direction:column;gap:7px}
.findbar .row{display:flex;align-items:center;gap:7px}
.findbar input{background:var(--page);border:1px solid var(--border-2);border-radius:8px;padding:5px 9px;font-size:12.5px;min-width:0;flex:1;font-family:inherit;color:var(--ink-1)}
.findbar input:focus{outline:none;border-color:var(--accent)}
.findbar .fcount{font-family:var(--mono);font-size:11.5px;color:var(--ink-3);min-width:52px;text-align:center;flex:none}
.findbar .fcount.none{color:var(--down)}
.findbar .lbl{font-size:11px;color:var(--ink-3);flex:none;width:26px}
.iconbtn{width:26px;height:26px;border-radius:8px;display:grid;place-items:center;color:var(--ink-2);flex:none;border:1px solid var(--border);background:none;cursor:pointer}
.iconbtn:hover{background:var(--panel-3);color:var(--ink-1)}
.prompt-editor{flex:1;min-height:0;display:flex;flex-direction:column;padding:12px 16px 0}
.prompt-editor textarea{flex:1;min-height:0;resize:none;background:var(--page);border:1px solid var(--border-2);border-radius:11px;padding:12px;font-size:13px;line-height:1.7;font-family:var(--mono);color:var(--ink-1)}
.prompt-editor textarea:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
.prompt-foot{flex:none;display:flex;align-items:center;gap:8px;padding:11px 16px 14px}
.prompt-foot .wc{font-size:11.5px;color:var(--ink-3);margin-right:auto}
</style>
