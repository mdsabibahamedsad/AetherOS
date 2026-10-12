import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  base: './',
  plugins: [react(), tailwindcss()],
  css: {
    // Pin an explicit (empty) PostCSS config. Tailwind is handled entirely by
    // `@tailwindcss/vite`, so the renderer needs no PostCSS plugins — and
    // without this, Vite's `postcss-load-config` walks UP the filesystem
    // looking for a stray `postcss.config.*` / `tailwind.config.*`. The desktop
    // build runs from inside the user's home tree (e.g.
    // `C:\Users\<name>\AppData\Local\hermes\aetheros\apps\desktop`), so an
    // unrelated Tailwind v3 config higher up the tree gets picked up and
    // reprocesses our v4 stylesheet, failing the build with
    // "`@layer base` is used but no matching `@tailwind base` directive is
    // present." Pinning the config makes the build hermetic.
    postcss: { plugins: [] }
  },
  build: {
    // Keep desktop packaging stable: Shiki ships many dynamic chunks by
    // default, and electron-builder can OOM scanning thousands of files.
    // Collapsing to a single chunk is intentional, so the renderer bundle is
    // large by design (~22 MB). Raise the warning ceiling above that so the
    // cosmetic "chunk larger than 500 kB" nag stays quiet, while still acting
    // as a regression alarm if the bundle balloons well past today's size.
    chunkSizeWarningLimit: 25000,
    rolldownOptions: {
      output: {
        // Master 24/27: enable route-level splitting (React.lazy sites in
        // desktop-controller). If packaged file:// loading ever regresses,
        // revisit with a custom preload handler — do not blanket-disable.
        codeSplitting: true,
        // Master 74127: isolate nanostores in its own leaf chunk. Every
        // code-split chunk calls the nanostores module initializer at its
        // top level (store files run `atom(...)` at module scope), while the
        // nanostores module itself lived in the entry chunk. The gateway
        // chunk is imported BY the entry graph, so it evaluated before the
        // entry body ran and the initializer binding was still unassigned —
        // every packaged boot crashed with "TypeError: i is not a function"
        // in gateway-*.js and the gateway never connected (the original
        // BACKEND running / GATEWAY disconnected symptom). A dedicated leaf
        // chunk evaluates before both importers, so the initializer is
        // always assigned before any chunk body runs.
        // Rolldown requires the function form (object form throws
        // "manualChunks is not a function" at build time).
        manualChunks: id => {
          if (/node_modules[\\/]nanostores([\\/]|$)/.test(id)) {
            return 'vendor-nanostores'
          }

          return undefined
        }
      }
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@aetheros/shared': path.resolve(__dirname, '../shared/dist/index.js'),
      react: path.resolve(__dirname, '../../node_modules/react'),
      'react-dom': path.resolve(__dirname, '../../node_modules/react-dom'),
      'react/jsx-dev-runtime': path.resolve(__dirname, '../../node_modules/react/jsx-dev-runtime.js'),
      'react/jsx-runtime': path.resolve(__dirname, '../../node_modules/react/jsx-runtime.js')
    },
    dedupe: ['react', 'react-dom']
  },
  server: {
    host: '127.0.0.1',
    port: 5174,
    strictPort: true
  },
  preview: {
    host: '127.0.0.1',
    port: 4174
  }
})
