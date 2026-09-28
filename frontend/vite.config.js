import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 构建号取本地时间（此前用 UTC 比本地慢 8 小时，显示困惑）
const d = new Date()
const p = n => String(n).padStart(2, '0')

export default defineConfig({
  define: { __APP_BUILD__: JSON.stringify(`${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`) },
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    proxy: { '/api': 'http://127.0.0.1:8765', '/files': 'http://127.0.0.1:8765' },
  },
})
