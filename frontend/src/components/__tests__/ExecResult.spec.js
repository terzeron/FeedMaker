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
});
