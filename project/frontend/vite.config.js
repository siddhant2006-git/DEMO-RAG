import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Vite does not auto-populate process.env from .env for this config file
  // (only import.meta.env in client code gets that treatment), so .env must
  // be loaded explicitly here for VITE_PROXY_TARGET below to take effect.
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5175,
      strictPort: true,
      proxy: {
        // Forwards same-origin /api/* calls to the backend, so the browser never
        // needs a hardcoded absolute API URL. VITE_PROXY_TARGET lets docker-compose
        // point this at the api container's Docker-network name (http://api:8000);
        // native `npm run dev` falls back to the backend's default local port.
        '/api': {
          target: env.VITE_PROXY_TARGET || 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
