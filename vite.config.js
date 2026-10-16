import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    babel({ presets: [reactCompilerPreset()] })
  ],
  server: {
    // Send /api/... requests to the FastAPI backend (see backend/), so the browser
    // sees one site and we don't need CORS
    proxy: {
      '/api': process.env.API_URL ?? 'http://localhost:8000',
    },
  },
})
