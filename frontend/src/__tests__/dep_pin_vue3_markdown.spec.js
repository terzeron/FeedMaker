/**
 * Dependency-pinning test for the external dependency `vue3-markdown`.
 *
 * Purpose
 * -------
 * Pin the VMarkdownView named export used by main.js. vue3-markdown is
 * registered globally as <VMarkdownView> but isn't currently invoked from
 * any template -- so this test focuses on the *import contract*: the
 * named export must remain a Vue component object the app can register.
 *
 * Reference call sites:
 *   src/main.js:54  import { VMarkdownView } from 'vue3-markdown';
 *   src/main.js:94  app.component('VMarkdownView', VMarkdownView);
 */

import { VMarkdownView } from "vue3-markdown";
import { createApp, h } from "vue";

describe("vue3-markdown: import surface", () => {
  test("VMarkdownView is a named export and a non-null value", () => {
    expect(VMarkdownView).toBeTruthy();
  });

  test("VMarkdownView is shaped like a Vue component (function or component-options object)", () => {
    // Vue accepts either a render function or an options object with a render/setup/template.
    const t = typeof VMarkdownView;
    expect(t === "object" || t === "function").toBe(true);
  });

  test("can be registered globally via app.component()", () => {
    // main.js:94 -- app.component('VMarkdownView', VMarkdownView)
    const app = createApp({ render: () => h("div") });
    expect(() => app.component("VMarkdownView", VMarkdownView)).not.toThrow();
    // Lookup should round-trip.
    expect(app.component("VMarkdownView")).toBe(VMarkdownView);
  });
});
