import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// UI_Decisions.md §2: Vite proxy forwards /api/* and /ws/* to FastAPI backend
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target:       'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws:     true,
      },
    },
  },
})
