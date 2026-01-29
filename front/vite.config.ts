import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    hmr: {
      // Если вы обращаетесь к приложению через localhost:8090,
      // HMR-клиент должен подключаться к тому же хосту и порту
      clientPort: 8090,
      overlay: true,
    },
    proxy: {
      '/api': {
        target: 'http://backend_full:8000',
        // ИЛИ target: 'http://127.0.0.1:8001', если запускаете фронт локально
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
