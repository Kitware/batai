import { sentryVitePlugin } from "@sentry/vite-plugin";
import path from 'path';
import { defineConfig } from 'vite';
import Vue from '@vitejs/plugin-vue';
import Vuetify from 'vite-plugin-vuetify';

// Defined by: https://developers.cloudflare.com/pages/configuration/build-configuration/#environment-variables
const GIT_SHA = process.env.CF_PAGES_COMMIT_SHA;

const subpath = process.env.VITE_APP_SUBPATH || '/';

// https://vitejs.dev/config/
export default defineConfig({
  base: subpath.endsWith('/') ? subpath : `${subpath}/`,
  envPrefix: 'VITE_APP_',
  plugins: [
    Vue(),
    Vuetify({
      autoImport: true
    }),
    sentryVitePlugin({
      org: "kitware-data",
      project: "bats-ai-client",
      release: {
        name: GIT_SHA,
      }
    }),
  ],
  server: {
    host: "0.0.0.0",
    port: 8080,
    proxy: {
      "/api": {
        target: `http://localhost:8000`,
        xfwd: true,
      },
    },
    strictPort: true,
  },
  build: {
    sourcemap: true
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@api': path.resolve(__dirname, './src/api'),
      '@components': path.resolve(__dirname, './src/components'),
      '@use': path.resolve(__dirname, './src/use'),
    },
  },
});
