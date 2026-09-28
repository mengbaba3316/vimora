<script setup>
import { computed, ref } from 'vue'
import { PALETTES, applyTheme, currentTheme } from './theme'
import logoMark from './assets/logo-mark.svg?raw'
import logoWord from './assets/logo-wordmark.svg?raw'

/* 配色板：初始值由 index.html/main.js 写在 <html> 上，这里只读与切换。
 * 选择持久化到 localStorage.theme（key 与 theme.css 的 token 块一一对应）。 */
const theme = ref(currentTheme())
const paletteOpen = ref(false)
const current = computed(() => PALETTES.find(p => p.key === theme.value))
const currentName = computed(() => current.value?.name || '配色板')

function pickTheme(key) {
  theme.value = key
  applyTheme(key)
  paletteOpen.value = false
}
</script>

<template>
  <div class="app-shell">
    <aside class="rail">
      <div class="brand" title="Vimora">
        <span class="brand-logo" v-html="logoMark"></span>
        <span class="brand-word" v-html="logoWord"></span>
      </div>
      <nav class="nav">
        <router-link to="/" class="nav-item" exact-active-class="on">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="5" rx="2"/><rect x="13" y="10" width="8" height="11" rx="2"/><rect x="3" y="13" width="8" height="8" rx="2"/></svg>
          生图工作台
        </router-link>
        <router-link to="/prompts" class="nav-item" active-class="on">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M4 5h16M4 10h10M4 15h16M4 20h7"/></svg>
          提示词库
        </router-link>
        <router-link to="/libraries" class="nav-item" active-class="on">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="4" width="18" height="16" rx="2.5"/><circle cx="9" cy="10" r="1.7"/><path d="M3.5 17.5l5-4.5 4 3.5 3.5-3 4.5 4"/></svg>
          素材库
        </router-link>
        <router-link to="/providers" class="nav-item" active-class="on">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="4" width="18" height="7" rx="2"/><rect x="3" y="13" width="18" height="7" rx="2"/><path d="M7 7.5h.01M7 16.5h.01"/></svg>
          API 源站
        </router-link>
        <router-link to="/history" class="nav-item" active-class="on">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/></svg>
          历史任务
        </router-link>
      </nav>
      <div class="rail-foot">
        <el-popover v-model:visible="paletteOpen" placement="top-start" :width="196" trigger="click">
          <template #reference>
            <button class="theme-btn" type="button" title="配色板"
                    :aria-label="'配色板（当前：' + currentName + '）'">
              <!-- 双色圆点显示当前配色 -->
              <span class="palette-dot" v-if="current">
                <span :style="{ background: current.c1 }"></span>
                <span :style="{ background: current.c2 }"></span>
              </span>
            </button>
          </template>
          <div class="palette-list">
            <button v-for="p in PALETTES" :key="p.key" class="palette-item"
                    :class="{ on: p.key === theme }" @click="pickTheme(p.key)">
              <span class="sw"><span :style="{ background: p.c1 }"></span><span :style="{ background: p.c2 }"></span></span>
              <span class="pn">{{ p.name }}</span>
              <svg v-if="p.key === theme" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M4 12.5l5 5L20 7"/></svg>
            </button>
          </div>
        </el-popover>
      </div>
    </aside>
    <main>
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-shell{display:flex;height:100vh;overflow:hidden}

/* ── 左轨（抄 prototype .rail）── */
.rail{width:216px;flex:none;background:var(--page);border-right:1px solid var(--border);display:flex;flex-direction:column;min-height:0}
.brand{display:flex;align-items:center;gap:11px;height:58px;flex:none;padding:0 16px;border-bottom:1px solid var(--border);color:var(--accent)}
.brand-logo :deep(svg){height:32px;width:auto;display:block}
.brand-word :deep(svg){height:14px;width:auto;display:block}
.nav{padding:14px 12px 14px 18px;flex:1;min-height:0;overflow-y:auto}
.nav-item{position:relative;width:100%;display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:11px;color:var(--ink-1);font-size:13.5px;font-weight:500;margin-bottom:2px;transition:background .15s ease,color .15s ease;text-align:left;text-decoration:none;cursor:pointer}
.nav-item svg{flex:none;opacity:1}
.nav-item:hover{background:var(--panel-2)}
.nav-item.on{background:var(--accent);color:var(--on-accent);font-weight:600}
.nav-item.on::after{content:"";position:absolute;left:0;top:8px;bottom:8px;width:3px;border-radius:0 3px 3px 0;background:var(--on-accent)}
.nav-item.on svg{opacity:1}

/* ── 左轨底部：主题切换 ── */
.rail-foot{flex:none;display:flex;align-items:center;gap:8px;padding:10px 12px;border-top:1px solid var(--border)}
.theme-btn{width:32px;height:32px;border-radius:10px;display:grid;place-items:center;background:var(--panel-2);border:1px solid var(--border);color:var(--ink-2);cursor:pointer;transition:background .15s ease,border-color .15s ease,color .15s ease;font-family:inherit;padding:0}
.theme-btn:hover{background:var(--panel-3);border-color:var(--border-2);color:var(--ink-1)}
/* 当前配色双色圆点 */
.palette-dot{display:flex}
.palette-dot span{width:11px;height:11px;border-radius:50%;display:block}
.palette-dot span:first-child{transform:translateX(2px)}
.palette-dot span:last-child{transform:translateX(-2px);border:1px solid var(--panel-2)}
main{flex:1;min-width:0;min-height:0;display:flex;flex-direction:column;overflow-y:auto;overflow-x:clip}
</style>

<style>
/* 配色板弹出列表：el-popover teleport 到 body，须用全局作用域 */
.palette-list{display:flex;flex-direction:column}
.palette-item{display:flex;align-items:center;gap:9px;width:100%;padding:7px 8px;border:0;border-radius:9px;background:none;font-family:inherit;font-size:12.5px;color:var(--ink-2);cursor:pointer;text-align:left}
.palette-item:hover{background:var(--panel-2)}
.palette-item.on{background:var(--panel-2);color:var(--ink-1);font-weight:600}
.palette-item .sw{display:flex;flex:none}
.palette-item .sw span{width:13px;height:13px;border-radius:50%;display:block}
.palette-item .sw span:first-child{transform:translateX(2px)}
.palette-item .sw span:last-child{transform:translateX(-2px);border:1px solid var(--panel-2)}
.palette-item .pn{flex:1;min-width:0}
</style>