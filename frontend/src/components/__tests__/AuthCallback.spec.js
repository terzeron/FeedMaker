import { mount } from "@vue/test-utils";
import AuthCallback from "../AuthCallback.vue";

// mockRoute는 useRoute가 반환하는 동일 참조이므로, 마운트 전 query를 바꿔
// `if (accessToken)`의 true/false 분기를 각각 검증할 수 있다.
const mockRoute = { query: { access_token: "abc" } };
const mockPush = vi.fn();

vi.mock("vue-router", () => ({
  useRoute: () => mockRoute,
  useRouter: () => ({ push: mockPush }),
}));

describe("AuthCallback.vue", () => {
  beforeEach(() => {
    mockPush.mockClear();
    mockRoute.query = { access_token: "abc" };
  });

  it("mounts without error and shows message", async () => {
    const wrapper = mount(AuthCallback);
    expect(wrapper.text()).toContain("로그인 중");
  });

  it("redirects to ExecResult when access_token is present", () => {
    mount(AuthCallback);
    expect(mockPush).toHaveBeenCalledWith({ name: "ExecResult" });
  });

  it("still redirects when access_token is absent", () => {
    // access_token이 없으면 if 블록(false 분기)을 건너뛰고도 정상적으로
    // ExecResult로 리디렉션해야 한다.
    mockRoute.query = {};
    mount(AuthCallback);
    expect(mockPush).toHaveBeenCalledWith({ name: "ExecResult" });
  });
});
