import vue from 'eslint-plugin-vue';
import babelParser from '@babel/eslint-parser';

const parserOptions = {
  ecmaVersion: 'latest',
  sourceType: 'module',
  requireConfigFile: false,
  babelOptions: {
    presets: ['@babel/preset-env']
  }
};

const globals = {
  // Node.js globals
  process: 'readonly',
  global: 'readonly',
  console: 'readonly',
  require: 'readonly',
  module: 'readonly',
  __dirname: 'readonly',

  // Browser globals
  window: 'readonly',
  document: 'readonly',
  localStorage: 'readonly',
  sessionStorage: 'readonly',
  fetch: 'readonly',

  // Vue globals
  defineProps: 'readonly',
  defineEmits: 'readonly',
  defineExpose: 'readonly',
  defineOptions: 'readonly',
  defineSlots: 'readonly',
  defineModel: 'readonly',
  withDefaults: 'readonly'
};

export default [
  ...vue.configs['flat/essential'],
  {
    files: ['**/*.js'],
    languageOptions: {
      parser: babelParser,
      parserOptions,
      globals
    }
  },
  {
    files: ['**/*.vue'],
    languageOptions: {
      parserOptions: {
        ...parserOptions,
        parser: babelParser
      },
      globals
    }
  },
  {
    files: ['**/*.{js,vue}'],
    rules: {
      // Core rules
      'no-unused-vars': 'warn',
      'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
      'no-debugger': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
      'prefer-const': 'warn',
      'no-var': 'error',

      // Vue 3 specific rules
      'vue/multi-word-component-names': 'off',
      'vue/no-unused-vars': 'warn',
      'vue/no-mutating-props': 'error',
      'vue/require-default-prop': 'warn',
      'vue/require-prop-types': 'warn',
      'vue/prefer-import-from-vue': 'warn',

      // Code quality
      'eqeqeq': ['error', 'always'],
      'brace-style': ['error', '1tbs']
    }
  }
];
