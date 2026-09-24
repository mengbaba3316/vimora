import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './theme.css'
import App from './App.vue'
import router from './router'

/* 主题：默认炭黑；仅当 localStorage.theme === 'light' 时用纯白。
 * index.html 内联脚本已在首屏绘制前设置过，这里兜底（两处逻辑一致）。 */
;(() => {
  const t = localStorage.getItem('theme') === 'light' ? 'light' : 'dark'
  const el = document.documentElement
  el.setAttribute('data-theme', t)
  el.classList.toggle('dark', t === 'dark')
})()

createApp(App).use(ElementPlus).use(router).mount('#app')
