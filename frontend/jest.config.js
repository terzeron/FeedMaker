module.exports = {
  testEnvironment: "jsdom",
  coverageProvider: "v8",
  moduleFileExtensions: ["js", "json", "vue"],
  testMatch: ["<rootDir>/src/**/*.spec.js"],
  transform: {
    "^.+\\.vue$": "@vue/vue3-jest",
    "^.+\\.m?[jt]sx?$": "babel-jest",
  },
  transformIgnorePatterns: ["/node_modules/(?!perfect-debounce/)"],
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
    "\\.(css|less|scss)$": "<rootDir>/test/__mocks__/styleMock.js",
  },
  testEnvironmentOptions: {
    customExportConditions: ["node", "node-addons"],
  },
  // 기본 `npm test`는 커버리지 미수집(속도 우선). 커버리지는 `npm run test:coverage`(--coverage)로 수집.
  collectCoverageFrom: [
    "<rootDir>/src/**/*.{js,vue}",
    "!<rootDir>/src/main.js",
    "!<rootDir>/src/**/index.js",
  ],
  coverageReporters: ["text", "lcov", "html"],
  coverageDirectory: "<rootDir>/coverage",
};
