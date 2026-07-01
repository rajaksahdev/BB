import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/  (test config lives in vitest.config.ts)
export default defineConfig({
  plugins: [react()],
});
