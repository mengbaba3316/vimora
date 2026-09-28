<script setup>
import { computed, ref } from 'vue'
import { PALETTES, applyTheme, currentTheme } from '../theme'

/* 配色板选择器：置于各页 view-head 右上角，选择持久化到 localStorage.theme */
const theme = ref(currentTheme())
const open = ref(false)
const current = computed(() => PALETTES.find(p => p.key === theme.value))

function pick(key) {
  theme.value = key
  applyTheme(key)
  open.value = false
}
</script>

<template>
  <el-popover v-model:visible="open" placement="bottom-end" :width="196" trigger="click">
    <template #reference>
      <button class="btn palette-btn" type="button" title="配色板" aria-label="配色板">
        <span class="palette-dot" v-if="current">
          <span :style="{ background: current.c1 }"></span>
          <span :style="{ background: current.c2 }"></span>
        </span>
      </button>
    </template>
    <div class="palette-list">
      <button v-for="p in PALETTES" :key="p.key" type="button" class="palette-item"
              :class="{ on: p.key === theme }" @click="pick(p.key)">
        <span class="sw"><span :style="{ background: p.c1 }"></span><span :style="{ background: p.c2 }"></span></span>
        <span class="pn">{{ p.name }}</span>
        <svg v-if="p.key === theme" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M4 12.5l5 5L20 7"/></svg>
      </button>
    </div>
  </el-popover>
</template>

<style>
/* 弹层 teleport 到 body，须全局作用域 */
.palette-list{display:flex;flex-direction:column}
.palette-item{display:flex;align-items:center;gap:9px;width:100%;padding:7px 8px;border:0;border-radius:9px;background:none;font-family:inherit;font-size:12.5px;color:var(--ink-2);cursor:pointer;text-align:left}
.palette-item:hover{background:var(--panel-2)}
.palette-item.on{background:var(--panel-2);color:var(--ink-1);font-weight:600}
.palette-item .sw{display:flex;flex:none}
.palette-item .sw span{width:13px;height:13px;border-radius:50%;display:block}
.palette-item .sw span:first-child{transform:translateX(2px)}
.palette-item .sw span:last-child{transform:translateX(-2px);border:1px solid var(--panel-2)}
.palette-item .pn{flex:1;min-width:0}
.palette-btn{padding:7px 11px}
</style>
