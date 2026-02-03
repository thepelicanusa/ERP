import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      // Only proxy API routes, NOT the frontend root.
      "/auth": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/email": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/mdm": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/inventory": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/inventory_wms": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/sales": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/purchasing": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/accounting": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/qms": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/mrp": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/planning": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/mes": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/docs": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/tasks": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/waves": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/exceptions": { target: "http://127.0.0.1:8000", changeOrigin: true },

      // health + openapi are handy too
      "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/openapi.json": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});

