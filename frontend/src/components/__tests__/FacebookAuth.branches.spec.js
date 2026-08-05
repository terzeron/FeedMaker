import { mount } from "@vue/test-utils";
import FacebookAuth from "../FacebookAuth.vue";

// window.FB가 이미 존재하면 loadFacebookSDK()가 즉시 isSdkLoaded를 세운다.
// 기존 FacebookAuth.spec.js는 SDK 미로드 상태만 다루므로 isInitialized()의
// `&&` 우변(window.FB 확인)이 평가되지 않는다.
describe("FacebookAuth.vue - SDK 로드 완료 상태", () => {
  let warnSpy, errorSpy;

  beforeEach(() => {
    delete window.FB;
    delete window.fbAsyncInit;
    warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    delete window.FB;
    warnSpy.mockRestore();
    errorSpy.mockRestore();
  });

  const mountLoaded = async () => {
    window.FB = { init: vi.fn(), login: vi.fn(), api: vi.fn() };
    const wrapper = mount(FacebookAuth, {
      props: { appId: "1234567890123456" },
    });
    await new Promise((r) => setTimeout(r));
    return wrapper;
  };

  it("SDK가 이미 로드되어 있으면 auth-initialized를 emit하고 isInitialized가 true다", async () => {
    const wrapper = await mountLoaded();

    expect(wrapper.emitted("auth-initialized")).toBeTruthy();
    expect(wrapper.vm.isInitialized()).toBe(true);
  });

  it("isSdkLoaded가 true라도 window.FB가 사라지면 isInitialized는 false다", async () => {
    const wrapper = await mountLoaded();

    delete window.FB;
    expect(wrapper.vm.isInitialized()).toBe(false);
  });
});
