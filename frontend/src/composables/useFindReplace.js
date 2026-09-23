import { ref, computed } from 'vue'

/*
 * 提示词局部查找 / 替换组合式函数（逻辑从原型 #view-workbench 移植）。
 * textRef：可读写的 ref（或可写 computed），指向提示词全文。
 * 大小写不敏感、按字面匹配（正则元字符转义）；jump 用原生 setSelectionRange 定位。
 */
export function useFindReplace(textRef) {
  const query = ref(''), replaceWith = ref(''), idx = ref(0), matches = ref([])
  const count = computed(() => matches.value.length)
  const label = computed(() => !query.value ? '0/0' : count.value ? `${idx.value + 1}/${count.value}` : '无结果')
  function rescan() {
    matches.value = []
    if (query.value) {
      const re = new RegExp(query.value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')
      let m
      while ((m = re.exec(textRef.value)) !== null) {
        matches.value.push(m.index)
        if (m.index === re.lastIndex) re.lastIndex++
      }
    }
    idx.value = 0
  }
  function jump(dir, editor) {
    if (!count.value) return
    idx.value = (idx.value + dir + count.value) % count.value
    const pos = matches.value[idx.value]
    editor.value?.focus()
    editor.value?.setSelectionRange(pos, pos + query.value.length)
    const line = textRef.value.slice(0, pos).split('\n').length
    editor.value.scrollTop = Math.max(0, (line - 4) * 22)
  }
  function replaceOne() {
    if (!count.value) return
    const pos = matches.value[idx.value]
    textRef.value = textRef.value.slice(0, pos) + replaceWith.value +
                    textRef.value.slice(pos + query.value.length)
    rescan()
  }
  function replaceAll() {
    if (!query.value) return 0
    const n = count.value
    textRef.value = textRef.value.replace(
      new RegExp(query.value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'), replaceWith.value)
    rescan()
    return n
  }
  return { query, replaceWith, label, rescan, jump, replaceOne, replaceAll }
}
