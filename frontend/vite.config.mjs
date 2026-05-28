import { fileURLToPath, URL } from 'node:url';

import basicSsl from '@vitejs/plugin-basic-ssl';
import vue from '@vitejs/plugin-vue';
import { defineConfig, loadEnv } from 'vite';

import generateVersionInfo from './generate-version.js';

function buildProcessEnv(mode) {
  const loaded = loadEnv(mode, process.cwd(), '');
  const base = loaded.BASE_URL || '/';
  const appEnv = Object.fromEntries(
    Object.entries(loaded).filter(
      ([key]) => key === 'BASE_URL' || key.startsWith('VUE_APP_')
    )
  );

  return {
    ...appEnv,
    NODE_ENV: mode,
    BASE_URL: base,
    VUE_APP_VERSION: mode === 'test' ? 'dev' : generateVersionInfo()
  };
}

export default defineConfig(({ mode }) => {
  const processEnv = buildProcessEnv(mode);

  return {
    base: processEnv.BASE_URL,
    plugins: [vue(), basicSsl()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    define: {
      'process.env': JSON.stringify(processEnv)
    },
    server: {
      host: '0.0.0.0',
      port: 8081,
      allowedHosts: true,
      hmr: {
        protocol: 'wss'
      }
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./vitest.setup.js'],
      include: ['src/**/*.spec.js'],
      coverage: {
        provider: 'v8',
        reporter: ['text', 'lcov', 'html'],
        reportsDirectory: 'coverage',
        include: ['src/**/*.{js,vue}'],
        exclude: ['src/main.js', 'src/**/index.js']
      }
    }
  };
});
