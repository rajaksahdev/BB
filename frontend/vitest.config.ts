import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Test-only config (kept separate from vite.config.ts so `tsc -b` in the build
// never type-checks vitest's types against @types/node).
export default defineConfig({
  plugins: [react()],
  // Automatic JSX runtime so test files need no explicit React import.
  esbuild: { jsx: "automatic", jsxImportSource: "react" },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    css: false,
  },
});
