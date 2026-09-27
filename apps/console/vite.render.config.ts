import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Serves render/ for scripts/render-assets.mjs. Not part of the production build.
export default defineConfig({ root: 'render', plugins: [react()], server: { port: 5199, strictPort: true } })
