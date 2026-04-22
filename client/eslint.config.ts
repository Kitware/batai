import { globalIgnores } from "eslint/config";
import pluginVue from "eslint-plugin-vue";
import {
  defineConfigWithVueTs,
  vueTsConfigs,
} from "@vue/eslint-config-typescript";

export default defineConfigWithVueTs(
  {
    name: "app/files-to-lint",
    files: ["**/*.{vue,ts,mts,tsx}"],
  },

  globalIgnores(["**/dist/**", "**/dist-ssr/**", "**/coverage/**"]),

  ...pluginVue.configs["flat/recommended"],
  vueTsConfigs.recommended,

  {
    rules: {
      "no-console": ["error", { allow: ["warn", "error"] }],
      "vue/valid-v-slot": ["error", { allowModifiers: true }],
      "vue/multi-word-component-names": "off",
    },
  },
);
