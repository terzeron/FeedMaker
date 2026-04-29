import { mount } from "@vue/test-utils";
import ExecResult from "../ExecResult.vue";
import axios from "axios";

jest.mock("axios");

jest.mock("vue-router", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock("markdown-it", () => ({
  __esModule: true,
  default: class MarkdownItMock {
    render(src) {
      return `<p>${src}</p>`;
    }
  },
}));

const flushPromises = () => new Promise((r) => setTimeout(r));

describe("ExecResult.vue", () => {
  it("renders markdown when authenticated", async () => {
    axios.get
      .mockResolvedValueOnce({ data: { is_authenticated: true } }) // auth/me
      .mockResolvedValueOnce({ data: { exec_result: "# Hello" } }); // exec_result

    const wrapper = mount(ExecResult, {
      global: {
        stubs: { "router-link": true, "router-view": true },
      },
    });

    await flushPromises();
    expect(wrapper.html()).toContain("Hello");
    expect(wrapper.text()).toContain("Feed Manager");
  });

  // unauthenticated redirect path is covered by mocking vue-router; we ensure no crash

  it("shows fallback message when exec_result is null/empty", async () => {
    axios.get
      .mockResolvedValueOnce({ data: { is_authenticated: true } }) // auth/me
      .mockResolvedValueOnce({ data: {} }); // exec_result with no exec_result field

    const wrapper = mount(ExecResult, {
      global: {
        stubs: { "router-link": true, "router-view": true },
      },
    });

    await flushPromises();
    expect(wrapper.html()).toContain("No execution result available");
  });

  it("shows error message when API request fails", async () => {
    axios.get
      .mockResolvedValueOnce({ data: { is_authenticated: true } }) // auth/me
      .mockRejectedValueOnce(new Error("Server error")); // exec_result fails

    const wrapper = mount(ExecResult, {
      global: {
        stubs: { "router-link": true, "router-view": true },
      },
    });

    await flushPromises();
    expect(wrapper.find(".alert-danger").exists()).toBe(true);
    expect(wrapper.text()).toContain("Error loading execution result");
  });

  it("redirects to /login when not authenticated", async () => {
    const pushMock = jest.fn();
    jest.spyOn(require("vue-router"), "useRouter").mockReturnValue({
      push: pushMock,
    });

    axios.get.mockResolvedValueOnce({
      data: { is_authenticated: false },
    });

    mount(ExecResult, {
      global: {
        stubs: { "router-link": true, "router-view": true },
      },
    });

    await flushPromises();
    expect(pushMock).toHaveBeenCalledWith("/login");
  });

  it("handles checkAuthStatus error gracefully", async () => {
    jest.spyOn(console, "error").mockImplementation(() => {});
    const pushMock = jest.fn();
    jest.spyOn(require("vue-router"), "useRouter").mockReturnValue({
      push: pushMock,
    });

    axios.get.mockRejectedValueOnce(new Error("Network error"));

    mount(ExecResult, {
      global: {
        stubs: { "router-link": true, "router-view": true },
      },
    });

    await flushPromises();
    // auth check fails → not authenticated → redirect
    expect(pushMock).toHaveBeenCalledWith("/login");
    console.error.mockRestore();
  });

  it("renderedMarkdown returns empty string when source is empty", async () => {
    jest.spyOn(console, "error").mockImplementation(() => {});
    axios.get
      .mockResolvedValueOnce({ data: { is_authenticated: true } })
      .mockResolvedValueOnce({ data: { exec_result: "some text" } });

    const wrapper = mount(ExecResult, {
      global: {
        stubs: { "router-link": true, "router-view": true },
      },
    });

    await flushPromises();
    // source.value를 빈 문자열로 설정
    wrapper.vm.source = "";
    // renderedMarkdown computed가 "" 반환하는지 확인
    expect(wrapper.vm.renderedMarkdown).toBe("");
    console.error.mockRestore();
  });

  it("renderedMarkdown returns source when md is null", async () => {
    jest.spyOn(console, "error").mockImplementation(() => {});
    axios.get
      .mockResolvedValueOnce({ data: { is_authenticated: true } })
      .mockResolvedValueOnce({ data: { exec_result: "raw text" } });

    const wrapper = mount(ExecResult, {
      global: {
        stubs: { "router-link": true, "router-view": true },
      },
    });

    await flushPromises();
    // md를 null로 설정하고 source에 텍스트가 있을 때 raw text 반환 확인
    wrapper.vm.md = null;
    wrapper.vm.source = "raw text fallback";
    expect(wrapper.vm.renderedMarkdown).toBe("raw text fallback");
    console.error.mockRestore();
  });

  it("renderedMarkdown returns source when md.render throws", async () => {
    jest.spyOn(console, "error").mockImplementation(() => {});
    axios.get
      .mockResolvedValueOnce({ data: { is_authenticated: true } })
      .mockResolvedValueOnce({ data: { exec_result: "## Test" } });

    const wrapper = mount(ExecResult, {
      global: {
        stubs: { "router-link": true, "router-view": true },
      },
    });

    await flushPromises();

    // MarkdownIt mock의 render 메서드를 throw하도록 오버라이드
    const MarkdownIt = require("markdown-it").default;
    const instances = MarkdownIt.mock ? MarkdownIt.mock.instances : null;
    // mock 클래스의 prototype render를 spy로 throw하게 설정
    const renderSpy = jest
      .spyOn(MarkdownIt.prototype, "render")
      .mockImplementation(() => {
        throw new Error("render failed");
      });

    wrapper.vm.source = "error source";
    const result = wrapper.vm.renderedMarkdown;
    // catch 블록에서 source.value || "" 반환
    expect(result).toBe("error source");

    renderSpy.mockRestore();
    console.error.mockRestore();
  });
});
