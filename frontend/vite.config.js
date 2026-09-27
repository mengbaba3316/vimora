import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  define: { __APP_BUILD__: JSON.stringify(new Date().toISOString().slice(5,16).replace('T',' ')) },
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    proxy: { '/api': 'http://127.0.0.1:8765', '/files': 'http://127.0.0.1:8765' },
  },
})
