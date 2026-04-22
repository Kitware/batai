import process from "node:process";
import { fileURLToPath, URL } from "node:url";
import { sentryVitePlugin } from "@sentry/vite-plugin";
import Vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";
import Vuetify, { transformAssetUrls } from "vite-plugin-vuetify";

// Build sanity check, to ensure environment is defined;
// this will not load from .env files (unless we used a different Vite syntax),
// but we set VITE_API_ROOT at the process level.
if (!process.env.VITE_API_ROOT) {
  throw new Error("VITE_API_ROOT must be defined.");
}

const subpath = process.env.VITE_SUBPATH || "/";

export default defineConfig({
  base: subpath.endsWith("/") ? subpath : `${subpath}/`,
  plugins: [
    Vue({
      template: { transformAssetUrls },
    }),
    Vuetify({
      autoImport: true,
    }),
    sentryVitePlugin({
      org: "kitware-data",
      project: "bats-ai-client",
      authToken: process.env.SENTRY_AUTH_TOKEN,
      release: {
        // Defined by: https://developers.cloudflare.com/pages/configuration/build-configuration/#environment-variables
        name: process.env.CF_PAGES_COMMIT_SHA,
      },
    }),
  ],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "@api": fileURLToPath(new URL("./src/api", import.meta.url)),
      "@components": fileURLToPath(
        new URL("./src/components", import.meta.url),
      ),
      "@use": fileURLToPath(new URL("./src/use", import.meta.url)),
    },
  },
  server: {
    port: 8080,
    strictPort: true,
  },
  preview: {
    port: 8080,
    strictPort: true,
  },
  build: {
    sourcemap: true,
  },
});
