import { mount } from "@vue/test-utils";
import Login from "../Login.vue";
import axios from "axios";
import { authStore } from "../../stores/authStore";

jest.mock("axios");

jest.mock("vue-router", () => ({
  useRouter: () => ({ push: jest.fn() }),
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
  },
};

const stubs = {
  "font-awesome-icon": true,
  FacebookAuth: FacebookAuthStub,
  ToastNotification: true,
};

const flushPromises = () => new Promise((r) => setTimeout(r));

describe("Login.vue", () => {
  let errorSpy;

  beforeEach(() => {
    axios.get.mockReset();
    axios.post.mockReset();
    authStore.clear();
    errorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    errorSpy.mockRestore();
  });

  it("logs in and redirects on success", async () => {
    // initial auth check: not authenticated
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: false } });
    // login API
    axios.post.mockResolvedValueOnce({ data: { status: "success" } });

    const wrapper = mount(Login, { global: { stubs } });
    await flushPromises();

    // click login button
    const btns = wrapper.findAll("button");
    expect(btns.length).toBeGreaterThan(0);
    await btns[0].trigger("click");
    await flushPromises();

    expect(axios.post).toHaveBeenCalled();
    expect(wrapper.text()).toContain("님으로 로그인하였습니다.");
  });

  it("shows logout when already authenticated and logs out", async () => {
    // initial auth check: authenticated
    axios.get.mockResolvedValueOnce({
      data: { is_authenticated: true, name: "Tester" },
    });
    axios.post.mockResolvedValueOnce({}); // logout API

    const wrapper = mount(Login, { global: { stubs } });
    await flushPromises();

    const logoutButton = wrapper
      .findAll("button")
      .find((b) => b.text().includes("로그아웃"));
    expect(logoutButton).toBeTruthy();
    await logoutButton.trigger("click");
    await flushPromises();

    expect(axios.post).toHaveBeenCalled();
    // After logout, login button should be visible again
    const loginButton = wrapper
      .findAll("button")
      .find((b) => b.text().includes("로그인"));
    expect(loginButton).toBeTruthy();
  });

  it("shows 403 error message when backend returns 403", async () => {
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: false } });
    axios.post.mockRejectedValueOnce({ response: { status: 403 } });

    const wrapper = mount(Login, { global: { stubs } });
    await flushPromises();

    const btns = wrapper.findAll("button");
    await btns[0].trigger("click");
    await flushPromises();

    // The notification prop is passed to ToastNotification (stubbed),
    // so we check the internal state via vm
    expect(wrapper.vm.notification.message).toContain("허용되지 않은 이메일");
  });

  it("shows error message when backend returns non-success status", async () => {
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: false } });
    axios.post.mockResolvedValueOnce({
      data: { status: "failure", message: "서버 오류" },
    });

    const wrapper = mount(Login, { global: { stubs } });
    await flushPromises();

    const btns = wrapper.findAll("button");
    await btns[0].trigger("click");
    await flushPromises();

    expect(wrapper.vm.notification.message).toContain("서버 오류");
  });

  it("shows generic error message on login error without response", async () => {
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: false } });
    axios.post.mockRejectedValueOnce(new Error("Network Error"));

    const wrapper = mount(Login, { global: { stubs } });
    await flushPromises();

    const btns = wrapper.findAll("button");
    await btns[0].trigger("click");
    await flushPromises();

    expect(wrapper.vm.notification.message).toContain("Network Error");
  });

  it("shows error notification when logout fails", async () => {
    axios.get.mockResolvedValueOnce({
      data: { is_authenticated: true, name: "Tester" },
    });
    axios.post.mockRejectedValueOnce(new Error("Logout failed"));

    const wrapper = mount(Login, { global: { stubs } });
    await flushPromises();

    const logoutButton = wrapper
      .findAll("button")
      .find((b) => b.text().includes("로그아웃"));
    await logoutButton.trigger("click");
    await flushPromises();

    expect(wrapper.vm.notification.message).toContain(
      "로그아웃 중 오류가 발생했습니다",
    );
  });

  it("shows SDK loading state when not initialized", async () => {
    const NotEmittingStub = {
      name: "FacebookAuth",
      template: "<div></div>",
      emits: ["auth-initialized"],
      methods: {
        login: () => Promise.resolve("token"),
        logout: () => Promise.resolve(),
        getProfile: () => Promise.resolve({ name: "T", email: "t@e.com" }),
        isInitialized: () => false,
      },
    };
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: false } });

    const wrapper = mount(Login, {
      global: {
        stubs: {
          ...stubs,
          FacebookAuth: NotEmittingStub,
        },
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("로그인 준비 중...");
  });

  it("shows SDK failed state and retry button", async () => {
    const FailingStub = {
      name: "FacebookAuth",
      template: "<div></div>",
      emits: ["auth-initialized", "auth-error"],
      mounted() {
        this.$emit("auth-error");
      },
      methods: {
        login: () => Promise.resolve("token"),
        logout: () => Promise.resolve(),
        getProfile: () => Promise.resolve({ name: "T", email: "t@e.com" }),
        isInitialized: () => false,
        retryLoadSDK: jest.fn().mockResolvedValue(undefined),
      },
    };
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: false } });

    const wrapper = mount(Login, {
      global: {
        stubs: {
          ...stubs,
          FacebookAuth: FailingStub,
        },
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("Facebook 로그인을 불러올 수 없습니다");
    const retryBtn = wrapper
      .findAll("button")
      .find((b) => b.text().includes("다시 시도"));
    expect(retryBtn).toBeTruthy();
  });

  it("shows name greeting when logged in", async () => {
    axios.get.mockResolvedValueOnce({
      data: { is_authenticated: true, name: "홍길동" },
    });

    const wrapper = mount(Login, { global: { stubs } });
    await flushPromises();

    expect(wrapper.text()).toContain("홍길동님으로 로그인하였습니다.");
  });

  it("shows warning when Facebook Auth is not initialized on login attempt", async () => {
    const NotReadyStub = {
      name: "FacebookAuth",
      template: "<div></div>",
      emits: ["auth-initialized"],
      mounted() {
        this.$emit("auth-initialized");
      },
      methods: {
        login: () => Promise.resolve("token"),
        logout: () => Promise.resolve(),
        getProfile: () => Promise.resolve({ name: "T", email: "t@e.com" }),
        isInitialized: () => false,
      },
    };
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: false } });

    const wrapper = mount(Login, {
      global: {
        stubs: {
          ...stubs,
          FacebookAuth: NotReadyStub,
        },
      },
    });
    await flushPromises();

    const btns = wrapper.findAll("button");
    await btns[0].trigger("click");
    await flushPromises();

    expect(wrapper.vm.notification.message).toContain("초기화되지 않았습니다");
  });

  it("shows error when profile has no email", async () => {
    const NoEmailStub = {
      name: "FacebookAuth",
      template: "<div></div>",
      emits: ["auth-initialized"],
      mounted() {
        this.$emit("auth-initialized");
      },
      methods: {
        login: () => Promise.resolve("token"),
        logout: () => Promise.resolve(),
        getProfile: () => Promise.resolve({ name: "T" }),
        isInitialized: () => true,
      },
    };
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: false } });

    const wrapper = mount(Login, {
      global: {
        stubs: {
          ...stubs,
          FacebookAuth: NoEmailStub,
        },
      },
    });
    await flushPromises();

    const btns = wrapper.findAll("button");
    await btns[0].trigger("click");
    await flushPromises();

    expect(wrapper.vm.notification.message).toContain(
      "프로필 정보를 가져올 수 없습니다",
    );
  });
});
