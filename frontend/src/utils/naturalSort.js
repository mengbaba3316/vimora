/*
 * 名称自然排序：让名称里的连续数字按数值比较（8-2 < 8-10），
 * 避免 String.sort 的字典序把 8-10 排在 8-2 前面。
 * 用 zh-Hans-CN Collator：numeric 开启数值段比较，sensitivity:'base' 忽略大小写差异。
 */

const collator = new Intl.Collator('zh-Hans-CN', { numeric: true, sensitivity: 'base' })

/* 倒序比较器：入参为两个名称字符串，b 应排在 a 前时返回负值。
 * 用法：list.sort((a, b) => naturalDesc(a.original_name, b.original_name)) */
export function naturalDesc(a, b) {
  return collator.compare(String(b ?? ''), String(a ?? ''))
}
