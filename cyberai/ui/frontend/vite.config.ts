import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

export default defineConfig({
  plugins: [react()],
  // Assets are served by the backend from its /static mount.
  base: "/static/",
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  build: {
    outDir: "../static",
    emptyOutDir: true, // clean rebuild of cyberai/ui/static
    sourcemap: false,
    chunkSizeWarningLimit: 900,
  },
  server: {
    port: 5173,
    strictPort: true,
    // Dev proxy: frontend on 5173, backend on 8710.
    proxy: {
      "/api": { target: "http://127.0.0.1:8710", changeOrigin: false },
    },
  },
});
