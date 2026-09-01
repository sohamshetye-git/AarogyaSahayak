import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@aarogya/shared-types": path.resolve(__dirname, "../../packages/shared-types"),
      "@aarogya/design-tokens": path.resolve(__dirname, "../../packages/design-tokens"),
      "@aarogya/api-client": path.resolve(__dirname, "../../packages/api-client"),
      "@aarogya/i18n": path.resolve(__dirname, "../../packages/i18n"),
      "@aarogya/location": path.resolve(__dirname, "../../packages/location"),
    },

  },
  server: {
    port: 3001,
    host: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
