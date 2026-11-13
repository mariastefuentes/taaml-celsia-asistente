import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// El frontend nunca habla con el modelo: todo pasa por la API (FastAPI) en el puerto 8000.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000" } },
});
