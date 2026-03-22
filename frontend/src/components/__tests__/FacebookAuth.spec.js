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
});
