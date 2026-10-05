/*
 * 比例 + 清晰度 → 像素串换算（工作台提交用）。
 * 通用规则：清晰度档位决定长边像素（1K=1024，依次翻倍到 4K=4096）；
 * 比例 w:h 按长短边对齐，短边 = round(长边 × 短/长) 再取整到 8 的倍数；
 * 返回 "宽x高"（宽在高前：横图宽为长边，竖图高为长边）。解析失败兜底 1024x1024。
 *
 * GPT Image 2 / 2.5 系（模型名 gpt-image-2 开头）走 OpenAI 官方自定义尺寸约束：
 * 两边均为 16 的倍数、每边 ≤ 3840、宽高比 ≤ 3:1、总像素 655,360 ~ 8,294,400。
 * 档位仍表示长边目标（4K 封顶 3840）；总像素超预算时长边逐级回退 16，
 * 低于下限（极端比例的小档位）则逐级上调 16，其余模型维持通用规则不受影响。
 */
const K_TO_LONG = { '1K': 1024, '2K': 2048, '3K': 3072, '4K': 4096 }
const GPT2_RE = /^gpt-image-2/
const GPT_MAX_EDGE = 3840
const GPT_MAX_PIXELS = 8294400
const GPT_MIN_PIXELS = 655360

function to8(n) {
  return Math.round(n / 8) * 8
}

function to16(n) {
  return Math.round(n / 16) * 16
}

/* GPT Image 2 系：返回 [长边, 短边]，保证 16 整除 + 边长/总像素预算全部合规 */
function gpt2Pair(rw, rh, long) {
  /* 比例超过 3:1 先钳到 3:1，避免算出必然被拒的极端尺寸 */
  if (Math.max(rw, rh) / Math.min(rw, rh) > 3) {
    if (rw > rh) { rh = rw / 3 } else { rw = rh / 3 }
  }
  const s = Math.min(rw, rh) / Math.max(rw, rh)
  let L = Math.min(long, GPT_MAX_EDGE)
  while (L > 16 && L * to16(L * s) > GPT_MAX_PIXELS) L -= 16
  while (L < GPT_MAX_EDGE && L * to16(L * s) < GPT_MIN_PIXELS) L += 16
  return [L, to16(L * s)]
}

export function ratioToSize(ratio, resolution, model) {
  try {
    const long = K_TO_LONG[String(resolution ?? '').trim().toUpperCase()]
    const m = String(ratio ?? '').trim().match(/^(\d+(?:\.\d+)?)\s*[:/]\s*(\d+(?:\.\d+)?)$/)
    if (!long || !m) return '1024x1024'
    const w = Number(m[1])
    const h = Number(m[2])
    if (!(w > 0) || !(h > 0)) return '1024x1024'
    const [L, S] = GPT2_RE.test(String(model ?? ''))
      ? gpt2Pair(w, h, long)
      : [long, to8(long * (Math.min(w, h) / Math.max(w, h)))]
    return w >= h ? `${L}x${S}` : `${S}x${L}`
  } catch {
    return '1024x1024'
  }
}
