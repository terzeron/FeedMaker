import { mount } from "@vue/test-utils";
import Login from "../Login.vue";
import axios from "axios";
import { authStore } from "../../stores/authStore";

const routerPushMock = vi.hoisted(() => vi.fn());

vi.mock("axios");

vi.mock("vue-router", () => ({
  useRouter: () => ({ push: routerPushMock }),
}));

const FacebookAuthStub = {
  name: "FacebookAuth",
  template: "<div></div>",
  emits: ["auth-initialized"],
  mounted() {
    this.$emit("auth-initialized");
  },
  methods: {
    login: () => Promise.resolve("token"),
    logout: () => Promise.resolve(),
    getProfile: () =>
      Promise.resolve({ name: "Tester", email: "t@example.com" }),
    isInitialized: () => true,
    retryLoadSDK: () => Promise.resolve(),
  },
};

const stubs = {
  "font-awesome-icon": true,
  FacebookAuth: FacebookAuthStub,
  ToastNotification: true,
};

const flushPromises = () => new Promise((r) => setTimeout(r));

describe("Login.vue - 미커버 분기", () => {
  let errorSpy;

  beforeEach(() => {
    routerPushMock.mockReset();
    axios.get.mockReset();
    axios.post.mockReset();
    authStore.clear();
    errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    errorSpy.mockRestore();
  });

  it("서버가 message 없이 실패하면 기본 실패 문구를 보여준다", async () => {
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: false } });
    axios.post.mockResolvedValueOnce({ data: { status: "failure" } });

    const wrapper = mount(Login, { global: { stubs } });
    await flushPromises();

    await wrapper.findAll("button")[0].trigger("click");
    await flushPromises();

    expect(wrapper.vm.notification.message).toBe("로그인 실패");
  });

  it("authRef가 없으면 retrySdk는 SDK 재로드를 건너뛴다", async () => {
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: false } });

    const wrapper = mount(Login, { global: { stubs } });
    await flushPromises();

    wrapper.vm.authRef = null;
    await wrapper.vm.retrySdk();

    expect(wrapper.vm.sdkFailed).toBe(false);
    expect(wrapper.vm.initialized).toBe(false);
  });

  it("로그아웃 중 컴포넌트가 사라지면 Facebook 로그아웃을 건너뛴다", async () => {
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: true } });

    const wrapper = mount(Login, { global: { stubs } });
    await flushPromises();

    const fbLogout = vi.spyOn(wrapper.vm.authRef, "logout");
    // 로그아웃 API 응답을 기다리는 사이 언마운트되면 template ref가 null이 된다.
    axios.post.mockImplementationOnce(() =>
      Promise.resolve().then(() => {
        wrapper.unmount();
        return {};
      }),
    );

    await wrapper.vm.logout();
    await flushPromises();

    expect(fbLogout).not.toHaveBeenCalled();

    expect(axios.post).toHaveBeenCalledWith(
      expect.stringContaining("/auth/logout"),
      {},
      { withCredentials: true },
    );
    expect(routerPushMock).toHaveBeenCalledWith("/login");
  });
});
