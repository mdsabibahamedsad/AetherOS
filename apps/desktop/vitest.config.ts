import { defineConfig } from 'vitest/config'
import path from 'path'

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      // Resolve the shared workspace from SOURCE, not committed dist output.
      // The test suite must exercise the current module contract; aliasing to
      // ../shared/dist/index.js made every @aetheros/shared assertion depend
      // on a prebuilt artifact (CI run #8: missing/stale dist surfaced as
      // "resolvePlatform is not a function"). Production bundling (vite.config.ts)
      // still consumes dist, which CI rebuilds explicitly before build/test.
      '@aetheros/shared': path.resolve(__dirname, '../shared/src/index.ts'),
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    exclude: [
      'build/**',
      'node_modules/**',
      'dist/**',
      'dist-packaged/**',
      'release/**',
      'electron/**/*.test.cjs',
      'scripts/**/*.test.cjs',
      // node:test guard suites (run via `node --test`, not vitest).
      'scripts/**/*.test.mjs',
    ],
  },
})
