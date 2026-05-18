/**
 * Dependency-pinning test for the external dependency `vue-router`.
 *
 * Purpose
 * -------
 * Pin the vue-router 4.x surface used by router/index.js and the
 * components that consume `useRouter()` / `useRoute()`. A v4 → v5 upgrade
 * or any rename of these helpers would break route guards silently.
 *
 * Reference call sites:
 *   src/router/index.js:1   import { createRouter, createWebHistory } from "vue-router";
 *   src/router/index.js:68  createRouter({ history: createWebHistory(...), routes })
 *   src/router/index.js:93  router.beforeEach(async (to, from, next) => ...)
 *   src/router/index.js:111 next({ path, query })
 *   src/components/Login.vue:158  router.push("/result")
 *   src/components/AuthCallback.vue:23  route.query.access_token
 *   src/components/AuthCallback.vue:32  router.push({ name: 'ExecResult' })
 */

import {
  createMemoryHistory,
  createRouter,
  createWebHistory,
} from "vue-router";

describe("vue-router: import surface", () => {
  test("createRouter and createWebHistory are callable", () => {
    expect(typeof createRouter).toBe("function");
    expect(typeof createWebHistory).toBe("function");
  });
});

describe("vue-router: createRouter({ history, routes }) call shape", () => {
  test("router exposes push / beforeEach / currentRoute", () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/", name: "Home", component: { template: "<div/>" } }],
    });
    expect(typeof router.push).toBe("function");
    expect(typeof router.beforeEach).toBe("function");
    // beforeEach(async (to, from, next) => ...) -- the guard signature
    expect(router.currentRoute).toBeTruthy();
  });
});

describe("vue-router: router.push() variants", () => {
  function build() {
    return createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/", name: "Home", component: { template: "<div/>" } },
        {
          path: "/result",
          name: "ExecResult",
          component: { template: "<div/>" },
        },
        { path: "/login", component: { template: "<div/>" } },
        {
          path: "/management/:group/:feed",
          name: "FeedManagementWithParams",
          component: { template: "<div/>" },
          props: true,
        },
      ],
    });
  }

  test("push(string) navigates by path", async () => {
    // Login.vue:158/205/249 -- router.push("/result"), ("/login")
    const router = build();
    await router.push("/result");
    expect(router.currentRoute.value.path).toBe("/result");
  });

  test("push({ name }) navigates by named route", async () => {
    // AuthCallback.vue:32 -- router.push({ name: 'ExecResult' })
    const router = build();
    await router.push({ name: "ExecResult" });
    expect(router.currentRoute.value.name).toBe("ExecResult");
  });

  test("push({ path, query }) preserves query as an object", async () => {
    // router/index.js:111 -- next({ path: "/login", query: { redirect: to.fullPath } })
    const router = build();
    await router.push({ path: "/login", query: { redirect: "/result" } });
    expect(router.currentRoute.value.path).toBe("/login");
    expect(router.currentRoute.value.query.redirect).toBe("/result");
  });

  test("dynamic-segment params are exposed on currentRoute.params", async () => {
    // FeedManagement.vue:1377 -- this.$route.params["group"], ["feed"]
    const router = build();
    await router.push("/management/news/cnn");
    expect(router.currentRoute.value.params.group).toBe("news");
    expect(router.currentRoute.value.params.feed).toBe("cnn");
  });
});

describe("vue-router: beforeEach guard signature", () => {
  test("beforeEach receives (to, from, next) and calling next() proceeds", async () => {
    // router/index.js:93 -- router.beforeEach(async (to, from, next) => { ... next() })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/", component: { template: "<div/>" } },
        {
          path: "/private",
          meta: { requiresAuth: true },
          component: { template: "<div/>" },
        },
        { path: "/login", component: { template: "<div/>" } },
      ],
    });

    const calls = [];
    router.beforeEach(async (to, from, next) => {
      calls.push({ toPath: to.path, fromPath: from.path });
      // production reads `to.matched` and `to.meta.requiresAuth`
      const requiresAuth = to.matched.some((r) => r.meta.requiresAuth);
      if (requiresAuth) {
        next({ path: "/login", query: { redirect: to.fullPath } });
      } else {
        next();
      }
    });

    await router.push("/private");
    // The guard redirected; check final landing.
    expect(router.currentRoute.value.path).toBe("/login");
    expect(router.currentRoute.value.query.redirect).toBe("/private");
    expect(calls.length).toBeGreaterThanOrEqual(1);
  });
});

describe("vue-router: route.query / route.params on currentRoute", () => {
  test("currentRoute.value exposes query as an object", async () => {
    // AuthCallback.vue:23 -- route.query.access_token
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/auth-callback", component: { template: "<div/>" } }],
    });
    await router.push("/auth-callback?access_token=abc&extra=1");
    expect(router.currentRoute.value.query.access_token).toBe("abc");
    expect(router.currentRoute.value.query.extra).toBe("1");
  });
});
