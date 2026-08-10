import { defineConfig } from "vitest/config";

// Dedicated config for the slow, shell-out E2E smoke test.
// It intentionally does NOT exclude test/e2e.test.ts (unlike the default
// vitest.config.ts used by `npm test`), so `npm run test:e2e` runs it.
export default defineConfig({
  test: {
    include: ["test/e2e.test.ts"],
    exclude: ["**/node_modules/**", "**/dist/**"],
  },
});
