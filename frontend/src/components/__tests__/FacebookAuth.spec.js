import { mount } from "@vue/test-utils";
import FacebookAuth from "../FacebookAuth.vue";

describe("FacebookAuth.vue", () => {
  let warnSpy, errorSpy;

  beforeEach(() => {
    delete window.FB;
    delete window.fbAsyncInit;
    warnSpy = jest.spyOn(console, "warn").mockImplementation(() => {});
    errorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    warnSpy.mockRestore();
    errorSpy.mockRestore();
  });

  it("renders without errors", () => {
    const wrapper = mount(FacebookAuth, {
      props: { appId: "test_app_id" },
    });
    expect(wrapper.find("span").exists()).toBe(true);
  });

  it("isInitialized returns false when FB is not loaded", () => {
    const wrapper = mount(FacebookAuth, {
      props: { appId: "test_app_id" },
    });
    expect(wrapper.vm.isInitialized()).toBe(false);
  });

  it("isInitialized returns false when isSdkLoaded is false even if window.FB exists", () => {
    window.FB = {};
    const wrapper = mount(FacebookAuth, {
      props: { appId: "test_app_id" },
    });
    // isSdkLoaded is still false because loadFacebookSDK rejects for test_app_id
    expect(wrapper.vm.isInitialized()).toBe(false);
  });

  it("exposes sdkLoadError when appId is not configured", async () => {
    const wrapper = mount(FacebookAuth, {
      props: { appId: "test_app_id" },
    });
    // Wait for onMounted to run
    await new Promise((r) => setTimeout(r));
    expect(wrapper.vm.sdkLoadError).toBe("Facebook App ID is not configured");
  });

  it("emits auth-error when SDK load fails", async () => {
    const wrapper = mount(FacebookAuth, {
      props: { appId: "test_app_id" },
    });
    await new Promise((r) => setTimeout(r));
    expect(wrapper.emitted("auth-error")).toBeTruthy();
    expect(wrapper.emitted("auth-error")[0][0]).toBe(
      "Facebook App ID is not configured",
    );
  });

  it("loads SDK and emits auth-initialized when FB already exists", async () => {
    window.FB = {
      init: jest.fn(),
      login: jest.fn(),
      logout: jest.fn(),
      getLoginStatus: jest.fn(),
      api: jest.fn(),
    };
    const wrapper = mount(FacebookAuth, {
      props: { appId: "real_app_id_123" },
    });
    await new Promise((r) => setTimeout(r));

    expect(wrapper.vm.isSdkLoaded).toBe(true);
    expect(wrapper.emitted("auth-initialized")).toBeTruthy();
  });

  it("login resolves with accessToken on connected status", async () => {
    window.FB = {
      init: jest.fn(),
      login: jest.fn((cb) =>
        cb({ authResponse: { accessToken: "tok123" }, status: "connected" }),
      ),
    };
    const wrapper = mount(FacebookAuth, {
      props: { appId: "real_app_id_123" },
    });
    await new Promise((r) => setTimeout(r));

    const token = await wrapper.vm.login();
    expect(token).toBe("tok123");
  });

  it("login rejects when user cancels", async () => {
    window.FB = {
      init: jest.fn(),
      login: jest.fn((cb) => cb({ authResponse: null })),
    };
    const wrapper = mount(FacebookAuth, {
      props: { appId: "real_app_id_123" },
    });
    await new Promise((r) => setTimeout(r));

    await expect(wrapper.vm.login()).rejects.toMatch("cancelled");
  });

  it("login rejects on non-connected status", async () => {
    window.FB = {
      init: jest.fn(),
      login: jest.fn((cb) =>
        cb({ authResponse: { accessToken: "t" }, status: "not_authorized" }),
      ),
    };
    const wrapper = mount(FacebookAuth, {
      props: { appId: "real_app_id_123" },
    });
    await new Promise((r) => setTimeout(r));

    await expect(wrapper.vm.login()).rejects.toMatch("Login failed");
  });

  it("logout calls FB.getLoginStatus and FB.logout when connected", async () => {
    const logoutFn = jest.fn((cb) => cb({}));
    window.FB = {
      init: jest.fn(),
      getLoginStatus: jest.fn((cb) => cb({ status: "connected" })),
      logout: logoutFn,
    };
    const wrapper = mount(FacebookAuth, {
      props: { appId: "real_app_id_123" },
    });
    await new Promise((r) => setTimeout(r));

    await wrapper.vm.logout();
    expect(logoutFn).toHaveBeenCalled();
  });

  it("logout resolves without calling FB.logout when not connected", async () => {
    window.FB = {
      init: jest.fn(),
      getLoginStatus: jest.fn((cb) => cb({ status: "unknown" })),
      logout: jest.fn(),
    };
    const wrapper = mount(FacebookAuth, {
      props: { appId: "real_app_id_123" },
    });
    await new Promise((r) => setTimeout(r));

    await wrapper.vm.logout();
    expect(window.FB.logout).not.toHaveBeenCalled();
  });

  it("getProfile resolves with user data", async () => {
    window.FB = {
      init: jest.fn(),
      api: jest.fn((path, opts, cb) =>
        cb({ id: "1", name: "Test", email: "t@e.com" }),
      ),
    };
    const wrapper = mount(FacebookAuth, {
      props: { appId: "real_app_id_123" },
    });
    await new Promise((r) => setTimeout(r));

    const profile = await wrapper.vm.getProfile();
    expect(profile.name).toBe("Test");
  });

  it("getProfile rejects on error response", async () => {
    window.FB = {
      init: jest.fn(),
      api: jest.fn((path, opts, cb) =>
        cb({ error: { message: "permission denied" } }),
      ),
    };
    const wrapper = mount(FacebookAuth, {
      props: { appId: "real_app_id_123" },
    });
    await new Promise((r) => setTimeout(r));

    await expect(wrapper.vm.getProfile()).rejects.toMatch("permission denied");
  });

  it("login throws when SDK is not loaded", async () => {
    const wrapper = mount(FacebookAuth, {
      props: { appId: "test_app_id" },
    });
    await new Promise((r) => setTimeout(r));

    await expect(wrapper.vm.login()).rejects.toThrow("not loaded");
  });

  it("logout throws when SDK is not loaded", async () => {
    const wrapper = mount(FacebookAuth, {
      props: { appId: "test_app_id" },
    });
    await new Promise((r) => setTimeout(r));

    await expect(wrapper.vm.logout()).rejects.toThrow("not loaded");
  });

  it("getProfile throws when SDK is not loaded", async () => {
    const wrapper = mount(FacebookAuth, {
      props: { appId: "test_app_id" },
    });
    await new Promise((r) => setTimeout(r));

    await expect(wrapper.vm.getProfile()).rejects.toThrow("not loaded");
  });

  it("retryLoadSDK resets error and retries", async () => {
    const wrapper = mount(FacebookAuth, {
      props: { appId: "test_app_id" },
    });
    await new Promise((r) => setTimeout(r));
    expect(wrapper.vm.sdkLoadError).toBeTruthy();

    await wrapper.vm.retryLoadSDK();
    // Still fails because appId is test_app_id
    expect(wrapper.vm.sdkLoadError).toBe("Facebook App ID is not configured");
  });

  it("waits for fbAsyncInit and resolves when FB becomes available", async () => {
    // Simulate fbAsyncInit already set, then FB becomes available
    window.fbAsyncInit = jest.fn();
    // FB will be set after a short delay
    setTimeout(() => {
      window.FB = { init: jest.fn() };
    }, 100);

    const wrapper = mount(FacebookAuth, {
      props: { appId: "real_app_id_123" },
    });

    // Wait enough for the 2000ms setTimeout in loadFacebookSDK
    await new Promise((r) => setTimeout(r, 2100));

    expect(wrapper.vm.isSdkLoaded).toBe(true);
  });

  it("rejects with timeout when fbAsyncInit is set but FB never loads", async () => {
    jest.useFakeTimers();
    // fbAsyncInit already set, but window.FB never becomes available
    window.fbAsyncInit = jest.fn();

    const wrapper = mount(FacebookAuth, {
      props: { appId: "real_app_id_123" },
    });

    // onMounted → loadFacebookSDK registers the 2000ms timeout synchronously;
    // advance past it, flushing the rejection through onMounted's catch
    await jest.advanceTimersByTimeAsync(2100);
    jest.useRealTimers();

    expect(wrapper.vm.sdkLoadError).toBe("Facebook SDK initialization timeout");
    expect(wrapper.emitted("auth-error")).toBeTruthy();
  });

  it("injects the SDK script and initializes when fbAsyncInit fires", async () => {
    // insertBefore needs a <script> sibling; clear any leftover SDK script
    document.getElementById("facebook-jssdk")?.remove();
    if (document.getElementsByTagName("script").length === 0) {
      document.head.appendChild(document.createElement("script"));
    }

    const wrapper = mount(FacebookAuth, {
      props: { appId: "real_app_id_123" },
    });
    await new Promise((r) => setTimeout(r));

    const injected = document.getElementById("facebook-jssdk");
    expect(injected).toBeTruthy();
    expect(injected.src).toContain("connect.facebook.net");

    // simulate the real SDK finishing load and invoking fbAsyncInit
    window.FB = { init: jest.fn() };
    window.fbAsyncInit();
    await new Promise((r) => setTimeout(r));

    expect(window.FB.init).toHaveBeenCalled();
    expect(wrapper.vm.isSdkLoaded).toBe(true);
    expect(wrapper.emitted("auth-initialized")).toBeTruthy();
  });

  it("sets sdkLoadError when the injected SDK script fails to load", async () => {
    document.getElementById("facebook-jssdk")?.remove();
    if (document.getElementsByTagName("script").length === 0) {
      document.head.appendChild(document.createElement("script"));
    }

    const wrapper = mount(FacebookAuth, {
      props: { appId: "real_app_id_123" },
    });
    await new Promise((r) => setTimeout(r));

    const injected = document.getElementById("facebook-jssdk");
    expect(injected).toBeTruthy();

    // simulate the browser failing to load the SDK script
    injected.onerror(new Error("network"));
    await new Promise((r) => setTimeout(r));

    // onerror rejects with the original error; onMounted's catch surfaces it
    // (the transient "Failed to load Facebook SDK" is overwritten by error.message)
    expect(wrapper.emitted("auth-error")).toBeTruthy();
    expect(wrapper.emitted("auth-error")[0][0]).toBe("network");
    expect(wrapper.vm.sdkLoadError).toBe("network");
  });
});
