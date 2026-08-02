import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true, // needed so the dev server is reachable from outside the container / Codespaces port-forward
  },
  preview: {
    port: 3000,
    host: true,
  },
});
