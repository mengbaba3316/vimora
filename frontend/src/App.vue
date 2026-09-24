<script setup>
import { ref } from 'vue'

/* 主题切换：初始值由 index.html/main.js 写在 <html> 上，这里只读与翻转。
 * 默认炭黑；手动选择持久化到 localStorage.theme。 */
const theme = ref(document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark')

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  document.documentElement.setAttribute('data-theme', theme.value)
  document.documentElement.classList.toggle('dark', theme.value === 'dark')
  localStorage.setItem('theme', theme.value)
}
</script>

<template>
  <div class="app-shell">
    <aside class="rail">
      <div class="brand">
        <div class="mk">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 3l1.9 5.6L20 10l-6.1 1.4L12 17l-1.9-5.6L4 10l6.1-1.4z"/></svg>
        </div>
        <b>生图工作台</b><span>v0.1</span>
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
        <button
          class="theme-btn"
          type="button"
          :title="theme === 'dark' ? '切换到纯白主题' : '切换到炭黑主题'"
          :aria-label="theme === 'dark' ? '切换到纯白主题' : '切换到炭黑主题'"
          @click="toggleTheme"
        >
          <!-- 炭黑下显示太阳（点击去纯白）；纯白下显示月亮（点击去炭黑） -->
          <svg v-if="theme === 'dark'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4.2"/><path d="M12 2.6v2.6M12 18.8v2.6M2.6 12h2.6M18.8 12h2.6M5.4 5.4l1.8 1.8M16.8 16.8l1.8 1.8M18.6 5.4l-1.8 1.8M7.2 16.8l-1.8 1.8"/></svg>
          <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20.6 14.2A8.4 8.4 0 019.8 3.4a8.4 8.4 0 1010.8 10.8z"/></svg>
        </button>
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
.brand{display:flex;align-items:center;gap:10px;height:58px;flex:none;padding:0 16px;border-bottom:1px solid var(--border)}
.brand .mk{width:28px;height:28px;border-radius:9px;flex:none;display:grid;place-items:center;background:var(--accent);color:var(--on-accent)}
.brand b{font-size:14.5px;font-weight:700;letter-spacing:-.01em;color:var(--ink-1)}
.brand span{font-size:10.5px;color:var(--ink-3);margin-left:auto;font-family:ui-monospace,"Cascadia Mono",Consolas,monospace}
.nav{padding:12px 10px;flex:1;min-height:0;overflow-y:auto}
.nav-item{position:relative;width:100%;display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:11px;color:var(--ink-2);font-size:13.5px;font-weight:500;margin-bottom:2px;transition:background .15s ease,color .15s ease;text-align:left;text-decoration:none;cursor:pointer}
.nav-item svg{flex:none;opacity:.75}
.nav-item:hover{background:var(--panel-2);color:var(--ink-1)}
.nav-item.on{background:var(--accent-soft);color:var(--accent);font-weight:600}
.nav-item.on::after{content:"";position:absolute;left:0;top:8px;bottom:8px;width:3px;border-radius:0 3px 3px 0;background:var(--accent)}
.nav-item.on svg{opacity:1}

/* ── 左轨底部：主题切换 ── */
.rail-foot{flex:none;display:flex;align-items:center;gap:8px;padding:10px 12px;border-top:1px solid var(--border)}
.theme-btn{width:32px;height:32px;border-radius:10px;display:grid;place-items:center;background:var(--panel-2);border:1px solid var(--border);color:var(--ink-2);cursor:pointer;transition:background .15s ease,border-color .15s ease,color .15s ease;font-family:inherit;padding:0}
.theme-btn:hover{background:var(--panel-3);border-color:var(--border-2);color:var(--ink-1)}

main{flex:1;min-width:0;min-height:0;display:flex;flex-direction:column;overflow-y:auto}
</style>
