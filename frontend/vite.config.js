import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/app/',  // Required for backend serving at /app; assets at /app/assets/

  server: {
    port: 5175,

    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },

      '/ai': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },

      '/patients': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },

      '/financial': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },

      '/appointments': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})