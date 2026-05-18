/**
 * Dependency-pinning test for the external dependency `axios`.
 *
 * Purpose
 * -------
 * Pin the axios surface used across frontend production code. An axios
 * upgrade that drops `defaults.withCredentials`, renames `isCancel`, or
 * changes the response object shape would silently break auth flow and
 * search cancellation.
 *
 * Reference call sites:
 *   src/main.js:17                axios.defaults.withCredentials = true;
 *   src/router/index.js:76        axios.get(url, { withCredentials: true });
 *   src/components/Login.vue:189  axios.post(url, body, { withCredentials: true });
 *   src/components/Login.vue:261  axios.get(...)
 *   src/components/Search.vue:179 axios.get(url, { signal });
 *   src/components/Search.vue:223 if (axios.isCancel(err)) return;
 *   src/components/ExecResult.vue:66 axios.get(path, { withCredentials: true });
 *   src/components/FeedManagement.vue various .get/.post/.put/.delete chained .then/.catch
 *
 * Strategy
 * --------
 * Don't hit real network. Mock the underlying XHR / adapter via axios's
 * own `axios.create({ adapter })` mechanism. That keeps the contract
 * (method shape, response object structure, cancel semantics) honest
 * without flaky CI.
 */

import axios from "axios";

describe("axios: import surface", () => {
  test("default export exposes HTTP methods used in production", () => {
    expect(typeof axios.get).toBe("function");
    expect(typeof axios.post).toBe("function");
    expect(typeof axios.put).toBe("function");
    expect(typeof axios.delete).toBe("function");
  });

  test("axios.defaults is a mutable object", () => {
    // main.js:17 -- axios.defaults.withCredentials = true
    expect(axios.defaults).toBeTruthy();
    expect(typeof axios.defaults).toBe("object");
  });

  test("axios.isCancel is callable", () => {
    // Search.vue:223 -- if (axios.isCancel(err)) return
    expect(typeof axios.isCancel).toBe("function");
  });

  test("axios.create returns a configured instance with the same methods", () => {
    const instance = axios.create();
    expect(typeof instance.get).toBe("function");
    expect(typeof instance.post).toBe("function");
  });
});

describe("axios: defaults.withCredentials", () => {
  test("withCredentials is a writable boolean on defaults", () => {
    const before = axios.defaults.withCredentials;
    axios.defaults.withCredentials = true;
    expect(axios.defaults.withCredentials).toBe(true);
    axios.defaults.withCredentials = before; // restore
  });
});

describe("axios: response object shape", () => {
  // Build a tiny axios instance whose adapter returns a canned response.
  function instanceReturning(canned) {
    return axios.create({
      adapter: (config) =>
        Promise.resolve({
          data: canned,
          status: 200,
          statusText: "OK",
          headers: {},
          config,
          request: {},
        }),
    });
  }

  test("get(url) resolves with res.data (the field production reads)", async () => {
    // FeedManagement.vue:826 -- res.data.status / res.data.feeds
    // Login.vue                -- response.data...
    const client = instanceReturning({
      status: "success",
      feeds: [{ name: "a" }],
    });
    const res = await client.get("/search");
    expect(res.data.status).toBe("success");
    expect(res.data.feeds).toEqual([{ name: "a" }]);
  });

  test("get(url, { withCredentials: true }) passes the option through", async () => {
    // router/index.js:76 / ExecResult.vue:66
    let seen;
    const client = axios.create({
      adapter: (config) => {
        seen = config;
        return Promise.resolve({
          data: {},
          status: 200,
          statusText: "OK",
          headers: {},
          config,
        });
      },
    });
    await client.get("/auth/me", { withCredentials: true });
    expect(seen.withCredentials).toBe(true);
    expect(seen.url).toBe("/auth/me");
    expect(seen.method).toBe("get");
  });

  test("post(url, body, config) forwards body as `data` config field", async () => {
    // Login.vue:189 -- axios.post(url, body, { withCredentials: true })
    let seen;
    const client = axios.create({
      adapter: (config) => {
        seen = config;
        return Promise.resolve({
          data: { ok: true },
          status: 200,
          statusText: "OK",
          headers: {},
          config,
        });
      },
    });
    await client.post(
      "/auth/login",
      { email: "a@b.c" },
      { withCredentials: true },
    );
    expect(seen.method).toBe("post");
    // axios serializes JSON bodies into config.data
    expect(JSON.parse(seen.data)).toEqual({ email: "a@b.c" });
    expect(seen.withCredentials).toBe(true);
  });
});

describe("axios: cancel / signal semantics", () => {
  test("AbortController signal + axios.isCancel(err) round-trip", async () => {
    // Search.vue:169/179/223 -- AbortController + signal + isCancel
    const controller = new AbortController();

    const pending = axios.get("https://example.invalid/never", {
      signal: controller.signal,
      // Adapter that resolves only when controller fires, simulating real
      // cancellation. axios converts an abort into a CanceledError.
      adapter: (config) =>
        new Promise((_, reject) => {
          config.signal.addEventListener("abort", () => {
            // Mimic axios's cancel behavior by throwing an error axios.isCancel
            // recognizes. The simplest way: import the public CanceledError.
            // eslint-disable-next-line global-require
            const { CanceledError } = require("axios");
            reject(new CanceledError("canceled"));
          });
        }),
    });

    controller.abort();

    try {
      await pending;
      throw new Error("should have rejected");
    } catch (err) {
      expect(axios.isCancel(err)).toBe(true);
    }
  });
});

describe("axios: chained .then(res => res.data...).catch(err => ...) shape", () => {
  test("promise chain delivers the response object to .then", async () => {
    // FeedManagement.vue:823-834 -- axios.get(url).then(res => ...).catch(err => ...)
    const client = axios.create({
      adapter: (config) =>
        Promise.resolve({
          data: { groups: ["g1"] },
          status: 200,
          statusText: "OK",
          headers: {},
          config,
        }),
    });
    let received;
    await client
      .get("/groups")
      .then((res) => {
        received = res.data;
      })
      .catch(() => {
        received = "error";
      });
    expect(received).toEqual({ groups: ["g1"] });
  });
});
