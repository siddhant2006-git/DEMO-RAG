import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // Forwards same-origin /api/* calls to the backend, so the browser never
      // needs a hardcoded absolute API URL. VITE_PROXY_TARGET lets docker-compose
      // point this at the api container's Docker-network name (http://api:8000);
      // native `npm run dev` falls back to the backend's default local port.
      '/api': {
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
