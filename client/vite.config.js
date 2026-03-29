import { sentryVitePlugin } from "@sentry/vite-plugin";
import path from 'path';
import { defineConfig } from 'vite';
import Vue from '@vitejs/plugin-vue';
import Vuetify from 'vite-plugin-vuetify';
import process from 'node:process';

const subpath = process.env.VITE_SUBPATH || '/';

// https://vitejs.dev/config/
export default defineConfig({
  base: subpath.endsWith('/') ? subpath : `${subpath}/`,
  plugins: [
    Vue(),
    Vuetify({
      autoImport: true
    }),
    sentryVitePlugin({
      org: "kitware-data",
      project: "bats-ai-client",
      authToken: process.env.SENTRY_AUTH_TOKEN,
      release: {
        // Defined by: https://developers.cloudflare.com/pages/configuration/build-configuration/#environment-variables
        name: process.env.CF_PAGES_COMMIT_SHA,
      }
    }),
  ],
  server: {
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
