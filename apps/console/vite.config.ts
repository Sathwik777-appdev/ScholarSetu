import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/health': {
        target: 'https://scholarsetu-api.onrender.com',
        changeOrigin: true,
      },
      '/v1': {
        target: 'https://scholarsetu-api.onrender.com',
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 4173,
    proxy: {
      '/health': {
        target: 'https://scholarsetu-api.onrender.com',
        changeOrigin: true,
      },
      '/v1': {
        target: 'https://scholarsetu-api.onrender.com',
        changeOrigin: true,
      },
    },
  },
  build: {
    sourcemap: false,
    // three.js (~900 kB before compression) stays in the lazily loaded 3D chunk; it is not preloaded.
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (/[\\/](recharts|d3-|victory)/.test(id)) return 'charts-vendor'
          if (/[\\/](react|react-dom|react-router|scheduler)[\\/]/.test(id)) return 'react-vendor'
          return undefined
        },
      },
    },
  },
})
