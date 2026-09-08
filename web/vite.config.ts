import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5176,
    proxy: {
      "/ask": "http://127.0.0.1:8080",
      "/resume": "http://127.0.0.1:8080",
      "/health": "http://127.0.0.1:8080",
    },
  },
});
