import { defineConfig } from 'eslint-define-config';
import vue from 'eslint-plugin-vue';
import babelParser from '@babel/eslint-parser';

export default defineConfig([
  {
    files: ['**/*.{js,vue}'],
    languageOptions: {
      parser: babelParser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        requireConfigFile: false,
        babelOptions: {
          presets: ['@babel/preset-env']
        }
      },
      globals: {
        // Node.js globals
        process: 'readonly',
        global: 'readonly',
        console: 'readonly',
        
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
      }
    },
    plugins: {
      vue
    },
    rules: {
      // ESLint recommended rules
      'no-unused-vars': 'warn',
      'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
      'no-debugger': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
      'prefer-const': 'warn',
      'no-var': 'error',
      
      // Vue 3 specific rules
      ...vue.configs['vue3-essential'].rules,
      'vue/multi-word-component-names': 'off',
      'vue/no-unused-vars': 'warn',
      'vue/script-setup-uses-vars': 'error',
      'vue/no-mutating-props': 'error',
      'vue/require-default-prop': 'warn',
      'vue/require-prop-types': 'warn',
      'vue/prefer-import-from-vue': 'warn',
      'vue/component-api-style': ['error', ['script-setup']],
      
      // Code quality
      'eqeqeq': ['error', 'always'],
      'curly': ['error', 'all'],
      'brace-style': ['error', '1tbs'],
      'comma-dangle': ['error', 'never'],
      'indent': ['error', 2],
      'quotes': ['error', 'single'],
      'semi': ['error', 'always']
    }
  },
  {
    files: ['**/*.vue'],
    languageOptions: {
      parser: vue.parser,
      parserOptions: {
        parser: babelParser,
        ecmaVersion: 'latest',
        sourceType: 'module'
      }
    }
  }
]);