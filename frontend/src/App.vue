<script setup>
import { onMounted, ref, watch } from 'vue'
import logoMark from './assets/logo-mark.svg?raw'
import logoWord from './assets/logo-wordmark.svg?raw'
import BuildTag from './components/BuildTag.vue'
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
        <BuildTag />
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
.brand{display:flex;align-items:center;gap:11px;height:58px;flex:none;padding:0 18px 0 30px;border-bottom:1px solid var(--border);color:var(--accent)}
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
.rail-foot{flex:none;display:flex;align-items:center;justify-content:center;padding:10px 12px;border-top:1px solid var(--border)}
.theme-btn{width:32px;height:32px;border-radius:10px;display:grid;place-items:center;background:var(--panel-2);border:1px solid var(--border);color:var(--ink-2);cursor:pointer;transition:background .15s ease,border-color .15s ease,color .15s ease;font-family:inherit;padding:0}
.theme-btn:hover{background:var(--panel-3);border-color:var(--border-2);color:var(--ink-1)}
main{flex:1;min-width:0;min-height:0;display:flex;flex-direction:column;overflow-y:auto;overflow-x:clip}
</style>

