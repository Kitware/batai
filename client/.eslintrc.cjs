module.exports = {
  root: true,
  env: {
    node: true,
    'vue/setup-compiler-macros': true,
  },
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-recommended',
    '@vue/typescript/recommended'
  ],
  rules: {
    // override/add rules settings here, such as:
    'no-console': ["error", { allow: ["warn", "error"] }],
    "@typescript-eslint/semi": ["error"],
    'vue/no-unused-vars': 'error',
    'vue/script-setup-uses-vars': 'error',
    "vue/valid-v-slot": ["error", {
      "allowModifiers": true
    }],
    'vue/multi-word-component-names': 'off'
  },
};