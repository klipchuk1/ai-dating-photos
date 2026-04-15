import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        rewrite: (path: string) => path.replace(/^\/api/, ""),
      },
      "/results": "http://localhost:8000",
      "/previews": "http://localhost:8000",
    },
  },
});
