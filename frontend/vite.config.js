// SmartLimo AI - Configuration Vite
//
// Configuration minimale : active seulement le plugin React officiel
// (support JSX, Fast Refresh en développement). Aucune option de build
// personnalisée (proxy API, alias de chemins...) n'est définie ici.
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
})
