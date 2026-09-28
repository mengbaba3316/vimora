<script setup>
import { onMounted, onUnmounted, ref } from 'vue'

/* 实时时钟：读本机时间，每秒刷新 */
const now = ref('')
let timer = null

function tick() {
  const d = new Date()
  const p = n => String(n).padStart(2, '0')
  now.value = `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

onMounted(() => { tick(); timer = setInterval(tick, 1000) })
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <span class="live-clock num">{{ now }}</span>
</template>

<style scoped>
.live-clock{font-size:11px;color:var(--ink-3);font-family:var(--mono);white-space:nowrap}
</style>
