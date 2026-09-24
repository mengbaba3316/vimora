/*
 * 比例 + 清晰度 → 像素串换算（工作台提交用）。
 * 规则：清晰度档位决定长边像素（1K=1024，依次翻倍到 4K=4096）；
 * 比例 w:h 按长短边对齐，短边 = round(长边 × 短/长) 再取整到 8 的倍数；
 * 返回 "宽x高"（宽在高前：横图宽为长边，竖图高为长边）。解析失败兜底 1024x1024。
 */
const K_TO_LONG = { '1K': 1024, '2K': 2048, '3K': 3072, '4K': 4096 }

function to8(n) {
  return Math.round(n / 8) * 8
}

export function ratioToSize(ratio, resolution) {
  try {
    const long = K_TO_LONG[String(resolution ?? '').trim().toUpperCase()]
    const m = String(ratio ?? '').trim().match(/^(\d+(?:\.\d+)?)\s*[:/]\s*(\d+(?:\.\d+)?)$/)
    if (!long || !m) return '1024x1024'
    const w = Number(m[1])
    const h = Number(m[2])
    if (!(w > 0) || !(h > 0)) return '1024x1024'
    const short = to8(long * (Math.min(w, h) / Math.max(w, h)))
    return w >= h ? `${long}x${short}` : `${short}x${long}`
  } catch {
    return '1024x1024'
  }
}
