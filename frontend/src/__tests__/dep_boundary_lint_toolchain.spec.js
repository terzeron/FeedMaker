/**
 * Dependency-boundary test for the lint toolchain
 * (@babel/*, eslint, eslint-plugin-vue, vue-eslint-parser).
 *
 * Purpose
 * -------
 * Records the judgment made when @babel/* (7 -> 8-rc) and vue-eslint-parser
 * (10.4.0 -> 10.4.1) were upgraded across major versions: those packages are
 * DEV TOOLS, not part of the shipped runtime bundle, so the upgrade cannot
 * affect service logic.
 *
 * That conclusion rests on two structural invariants. If either breaks, the
 * "no runtime impact" reasoning no longer holds and this test fails:
 *
 *   1. The toolchain lives in devDependencies, never dependencies. Vite bundles
 *      `dependencies` into the shipped app; `devDependencies` never reach it.
 *   2. Service code under src/ never imports @babel / eslint / vue-eslint-parser.
 *      @babel is referenced ONLY by frontend/eslint.config.mjs (the lint
 *      parser), which is outside src/ and outside the bundle.
 *
 * Behavioral regression is covered by the build (vite) and the unit suite
 * (vitest). This test pins the *structural reason* those tools stay off the
 * runtime path — so a future change that drags them into the bundle is caught.
 */

import { readFileSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const frontendRoot = join(here, "..", "..");
const srcDir = join(here, "..");

const pkg = JSON.parse(
  readFileSync(join(frontendRoot, "package.json"), "utf8"),
);

// Packages that must remain dev-only tooling.
const TOOLCHAIN = [
  "@babel/core",
  "@babel/eslint-parser",
  "@babel/preset-env",
  "eslint",
  "eslint-plugin-vue",
  "vue-eslint-parser",
];

const isToolchainName = (name) =>
  name.startsWith("@babel/") || /eslint/.test(name);

describe("lint toolchain boundary: package.json classification", () => {
  test("no @babel/eslint toolchain leaks into runtime dependencies", () => {
    const runtime = Object.keys(pkg.dependencies ?? {});
    const leaked = runtime.filter(isToolchainName);
    expect(leaked).toEqual([]);
  });

  test("the upgraded toolchain packages stay in devDependencies", () => {
    const dev = pkg.devDependencies ?? {};
    for (const name of TOOLCHAIN) {
      expect(dev).toHaveProperty(name);
    }
  });
});

describe("lint toolchain boundary: src/ never imports the toolchain", () => {
  const collectSourceFiles = (dir) => {
    const out = [];
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      // Tests reference tool names by design (this file included); exclude them.
      if (entry.name === "__tests__") continue;
      const full = join(dir, entry.name);
      if (entry.isDirectory()) {
        out.push(...collectSourceFiles(full));
      } else if (/\.(js|mjs|vue)$/.test(entry.name)) {
        out.push(full);
      }
    }
    return out;
  };

  const sourceFiles = collectSourceFiles(srcDir);

  // Matches `import ... from '<tool>'` and `require('<tool>')`.
  const FORBIDDEN_IMPORT =
    /(?:import[^'"]*from\s+|require\(\s*)['"](?:@babel\/[^'"]+|eslint[^'"]*|vue-eslint-parser)['"]/;

  test("the scan actually found source files (guards against a vacuous pass)", () => {
    expect(sourceFiles.length).toBeGreaterThan(0);
  });

  test("no service file imports @babel / eslint / vue-eslint-parser", () => {
    const offenders = sourceFiles.filter((f) =>
      FORBIDDEN_IMPORT.test(readFileSync(f, "utf8")),
    );
    expect(offenders).toEqual([]);
  });
});
