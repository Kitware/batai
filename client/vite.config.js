import path from 'path';
import { defineConfig } from 'vite';
import Vue from '@vitejs/plugin-vue';
import Vuetify from '@vuetify/vite-plugin';

// https://vitejs.dev/config/
export default defineConfig({
  envPrefix: 'VUE_APP_',
  define: {
    // Populated by netlify https://docs.netlify.com/configure-builds/environment-variables/
    __COMMIT_HASH__: JSON.stringify(process.env.COMMIT_REF || ''),
  },
  plugins: [
    Vue(),
    Vuetify({
      autoImport: true
    }),
  ],
  alias: {
    '@': path.resolve(__dirname, './src'),
  },
});
