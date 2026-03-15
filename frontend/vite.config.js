import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],

  base: '/app/',

  server: {
    port: 5175,

    proxy: {
      '^/(api|ai|patients|financial|appointments)': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})