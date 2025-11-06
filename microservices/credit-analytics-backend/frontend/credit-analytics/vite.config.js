import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  base: './',
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8100',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: '../../../../frontend/client/widgets/refinance',
    emptyOutDir: true,
  },
})
