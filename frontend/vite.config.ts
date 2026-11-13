import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { configDefaults, defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    // Emit every asset as a file: inlined data: URIs would be blocked by the
    // Content-Security-Policy (default-src 'self') set in infra/Caddyfile.
    assetsInlineLimit: 0,
  },
  server: {
    // In production FastAPI serves the built app and the API from one origin.
    // The dev server forwards API calls so the browser sees the same shape.
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    // Playwright runs e2e/ against the real stack (`npm run e2e`), not Vitest.
    exclude: [...configDefaults.exclude, "e2e/**"],
  },
});
