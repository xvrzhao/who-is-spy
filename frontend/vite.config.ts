import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// 开发期代理：SSE 请求均为 POST，EventSource 不可用；且后端 ALLOW_ORIGINS 默认为空，
// 走 proxy 同源访问可完全绕开 CORS
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    strictPort: true, // 端口被占时直接报错，避免悄悄换端口（ALLOW_ORIGINS 也只配了 5173）
    proxy: {
      // 后端路由统一挂在 /api 前缀下（src/domains/__init__.py）
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // SSE 必须关闭缓冲，否则 Vite 代理会攒满 buffer 才下发，前端收不到实时事件
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            proxyRes.headers['cache-control'] = 'no-cache'
            proxyRes.headers['x-accel-buffering'] = 'no'
          })
        },
      },
    },
  },
})
