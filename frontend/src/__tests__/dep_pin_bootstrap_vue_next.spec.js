/**
 * Dependency-pinning test for the external dependency `bootstrap-vue-next`.
 *
 * Purpose
 * -------
 * Pin the named-export surface of bootstrap-vue-next that main.js imports
 * and registers as global components. A bvn upgrade that renames any
 * component (e.g. BFormCheckbox → BCheckbox) or drops `createBootstrap`
 * would break the entire UI silently at runtime.
 *
 * Reference call sites:
 *   src/main.js:20-52 imports 30 named components + createBootstrap
 *   src/main.js:60    app.use(createBootstrap())
 *   src/main.js:63-92 app.component('BButton', BButton) ... etc.
 */

import {
  BAlert,
  BButton,
  BCard,
  BCardBody,
  BCardHeader,
  BCardText,
  BCol,
  BContainer,
  BForm,
  BFormCheckbox,
  BFormGroup,
  BFormInput,
  BFormRadio,
  BFormSelect,
  BInputGroup,
  BInputGroupText,
  BModal,
  BNav,
  BNavItem,
  BProgress,
  BProgressBar,
  BRow,
  BSpinner,
  BTable,
  BTableSimple,
  BTbody,
  BTd,
  BTh,
  BThead,
  BTr,
  createBootstrap,
} from "bootstrap-vue-next";
import { createApp, h } from "vue";

// One-to-one with the imports in src/main.js.
const REGISTERED_COMPONENTS = {
  BButton,
  BAlert,
  BCard,
  BCardText,
  BTable,
  BProgress,
  BContainer,
  BRow,
  BCol,
  BForm,
  BFormGroup,
  BFormInput,
  BFormSelect,
  BFormCheckbox,
  BFormRadio,
  BModal,
  BNav,
  BNavItem,
  BTableSimple,
  BThead,
  BTbody,
  BTr,
  BTh,
  BTd,
  BProgressBar,
  BInputGroup,
  BInputGroupText,
  BCardHeader,
  BCardBody,
  BSpinner,
};

describe("bootstrap-vue-next: createBootstrap plugin export", () => {
  test("createBootstrap is a callable factory", () => {
    // main.js:51/60 -- app.use(createBootstrap())
    expect(typeof createBootstrap).toBe("function");
    const plugin = createBootstrap();
    expect(plugin).toBeTruthy();
    // A Vue plugin must be either a function or an object with .install
    const t = typeof plugin;
    expect(
      t === "function" ||
        (t === "object" && typeof plugin.install === "function"),
    ).toBe(true);
  });

  test("createBootstrap()'s return value can be passed to app.use()", () => {
    // main.js:60 -- app.use(createBootstrap())
    const app = createApp({ render: () => h("div") });
    expect(() => app.use(createBootstrap())).not.toThrow();
  });
});

describe("bootstrap-vue-next: every component used in main.js is a named export", () => {
  test.each(Object.entries(REGISTERED_COMPONENTS))(
    "%s is exported (truthy)",
    (name, cmp) => {
      expect(cmp).toBeTruthy();
    },
  );

  test.each(Object.entries(REGISTERED_COMPONENTS))(
    "%s is shaped like a Vue component",
    (name, cmp) => {
      // Either a render function or an options object.
      const t = typeof cmp;
      expect(t === "function" || t === "object").toBe(true);
    },
  );

  test("app.component() accepts every one of the registered components", () => {
    // main.js:63-92 registers all components on the app instance.
    const app = createApp({ render: () => h("div") });
    for (const [name, cmp] of Object.entries(REGISTERED_COMPONENTS)) {
      expect(() => app.component(name, cmp)).not.toThrow();
    }
  });
});
