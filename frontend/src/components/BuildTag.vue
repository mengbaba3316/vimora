<script setup>
/* 构建号（MM-DD HH:mm，vite 注入）：用于识别浏览器缓存的旧页面 */
const build = __APP_BUILD__
</script>

<template>
  <span class="build-tag num" :title="`页面构建号 ${build}，与导航处构建号不一致说明命中了缓存旧页`">{{ build }}</span>
</template>

<style scoped>
.build-tag{font-size:11px;color:var(--ink-3);font-family:var(--mono);white-space:nowrap}
</style>
