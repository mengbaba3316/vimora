<script setup>
import { locale } from '../i18n'

/* 中英文切换：点击在 中文/English 间翻转，按钮显示目标语言 */
function toggle() {
  locale.value = locale.value === 'zh' ? 'en' : 'zh'
}
</script>

<template>
  <button class="btn lang-btn" type="button" title="中文 / English" @click="toggle">
    <!-- 地球图标 -->
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 3.8 5.7 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.7-3.8-9s1.3-6.4 3.8-9z"/></svg>
    <span class="lang-tag">{{ locale === 'zh' ? 'EN' : '中文' }}</span>
  </button>
</template>

<style>
.lang-btn{display:inline-flex;align-items:center;gap:5px}
.lang-tag{font-size:11px;font-weight:700;font-family:var(--mono)}
</style>
