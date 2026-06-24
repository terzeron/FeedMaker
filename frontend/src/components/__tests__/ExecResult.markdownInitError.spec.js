import { mount } from "@vue/test-utils";
import ExecResult from "../ExecResult.vue";
import axios from "axios";

const routerPushMock = vi.hoisted(() => vi.fn());

vi.mock("axios");

vi.mock("vue-router", () => ({
  useRouter: () => ({ push: routerPushMock }),
}));

// markdown-it 생성자가 throw 하도록 모킹하여 initMarkdownIt()의 catch 분기를 탄다.
// (모듈 단위 격리 덕분에 ExecResult의 MarkdownIt/md 싱글톤이 초기 null 상태로 시작됨)
vi.mock("markdown-it", () => ({
  __esModule: true,
  default: class ThrowingMarkdownIt {
    constructor() {
      throw new Error("markdown-it init failed");
    }
  },
}));

const flushPromises = () => new Promise((r) => setTimeout(r));

describe("ExecResult.vue - markdown-it init error", () => {
  it("logs an error and still mounts when markdown-it constructor throws", async () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    axios.get
      .mockResolvedValueOnce({ data: { is_authenticated: true } }) // auth/me
      .mockResolvedValueOnce({ data: { exec_result: "# Hello" } }); // exec_result

    const wrapper = mount(ExecResult, {
      global: {
        stubs: { "router-link": true, "router-view": true },
      },
    });

    await flushPromises();

    expect(errorSpy).toHaveBeenCalledWith(
      "Failed to initialize markdown-it:",
      expect.any(Error),
    );
    // 초기화 실패해도 컴포넌트는 정상 렌더링되어야 한다.
    expect(wrapper.exists()).toBe(true);
    errorSpy.mockRestore();
  });
});
