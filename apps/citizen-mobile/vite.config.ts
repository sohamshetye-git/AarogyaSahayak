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
    },
  },
  server: {
    port: 3001,
    host: true,
  },
});
