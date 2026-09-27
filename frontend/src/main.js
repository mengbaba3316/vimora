import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './theme.css'
import { applyTheme, currentTheme } from './theme'
import App from './App.vue'
import router from './router'

/* 配色板兜底：index.html 内联脚本已在首屏绘制前应用过，这里再校一次（两处逻辑一致） */
applyTheme(currentTheme())

createApp(App).use(ElementPlus).use(router).mount('#app')
