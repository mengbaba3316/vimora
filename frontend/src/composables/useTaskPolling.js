import { onMounted, onUnmounted } from 'vue'

/*
 * 任务列表轮询（规格 §7.6 / 原型「排队 / 生成中的任务每 2 秒自动刷新状态」）：
 * 每 2 秒 tick 一次；仅当 hasActive()（当前列表存在 queued/running）时
 * 才调 refresh(false) 静默拉取（不带 loading 态），避免无谓请求。
 */
export function useTaskPolling(refresh, hasActive) {
  let timer = null
  async function tick() {
    if (hasActive()) await refresh(false)
  }
  onMounted(() => { timer = setInterval(tick, 2000); tick() })
  onUnmounted(() => clearInterval(timer))
}
