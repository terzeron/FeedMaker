/**
 * Dependency-pinning test for the external dependency `vue`.
 *
 * Purpose
 * -------
 * Pin the Vue 3 Composition API surface used across src/. A future Vue
 * upgrade that renames `ref`, changes the `reactive()` proxy semantics,
 * or drops `defineExpose` would break the components silently at runtime.
 *
 * Reference call sites:
 *   src/main.js                     createApp(App)
 *   src/components/Login.vue        ref(initial) / computed(() => ...) / onMounted(async () => ...)
 *   src/components/Search.vue       reactive({ ... }) + computed
 *   src/components/Problems.vue     ref + computed + defineExpose
 *   src/components/FeedManagement.vue ref + onMounted
 */

import {
  ref,
  computed,
  reactive,
  createApp,
  onMounted,
  defineComponent,
  h,
  nextTick,
  isRef,
  isReactive,
} from "vue";

describe("vue: import surface", () => {
  test("composition-api primitives are callable", () => {
    expect(typeof ref).toBe("function");
    expect(typeof computed).toBe("function");
    expect(typeof reactive).toBe("function");
    expect(typeof onMounted).toBe("function");
  });

  test("createApp is the app factory", () => {
    expect(typeof createApp).toBe("function");
  });

  test("defineExpose exists on the module namespace", () => {
    // <script setup> auto-imports defineExpose, but components also import it
    // explicitly (Problems.vue:2 -- `import { ref, computed, defineExpose }`).
    // The symbol must remain reachable on the named export surface.
    // eslint-disable-next-line global-require
    const vue = require("vue");
    expect(vue).toHaveProperty("defineExpose");
  });
});

describe("vue: ref(initial) call shape", () => {
  test("ref(value) returns an object with .value equal to the initial", () => {
    const r = ref(0);
    expect(isRef(r)).toBe(true);
    expect(r.value).toBe(0);
  });

  test("ref(null) is the production pattern for empty handles", () => {
    // Login.vue: const authRef = ref(null); ... authRef.value = something
    const r = ref(null);
    expect(r.value).toBeNull();
    r.value = { name: "x" };
    expect(r.value.name).toBe("x");
  });

  test("ref(boolean) toggles via .value reassignment", () => {
    const flag = ref(false);
    expect(flag.value).toBe(false);
    flag.value = true;
    expect(flag.value).toBe(true);
  });
});

describe("vue: reactive(obj) call shape", () => {
  test("reactive returns a proxy whose mutations are observable", () => {
    // Search.vue passes a plain object literal to reactive(...).
    const state = reactive({ keyword: "", results: [] });
    expect(isReactive(state)).toBe(true);
    state.keyword = "abc";
    expect(state.keyword).toBe("abc");
  });
});

describe("vue: computed(getter) call shape", () => {
  test("computed exposes a read-only .value derived from getter", () => {
    const a = ref(2);
    const doubled = computed(() => a.value * 2);
    expect(doubled.value).toBe(4);
    a.value = 5;
    expect(doubled.value).toBe(10);
  });
});

describe("vue: onMounted hook signature", () => {
  test("onMounted accepts an async function and the component mounts it", async () => {
    let mounted = false;
    const Cmp = defineComponent({
      setup() {
        // Production: onMounted(async () => { ... await fetch ... })
        onMounted(async () => {
          mounted = true;
        });
        return () => h("div");
      },
    });
    const app = createApp(Cmp);
    const host = document.createElement("div");
    app.mount(host);
    await nextTick();
    expect(mounted).toBe(true);
    app.unmount();
  });
});

describe("vue: createApp(...) + mount + unmount lifecycle", () => {
  test("createApp returns an app instance with mount/unmount/component/use", () => {
    const app = createApp({ render: () => h("div", "ok") });
    expect(typeof app.mount).toBe("function");
    expect(typeof app.unmount).toBe("function");
    expect(typeof app.component).toBe("function"); // main.js:63+ -- app.component(...)
    expect(typeof app.use).toBe("function"); // main.js:60/95 -- app.use(...)
  });

  test("mount(elementOrSelector) renders into the DOM", () => {
    const host = document.createElement("div");
    const app = createApp({ render: () => h("p", "hello-vue") });
    app.mount(host);
    expect(host.textContent).toBe("hello-vue");
    app.unmount();
  });
});
