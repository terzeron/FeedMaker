import { mount } from "@vue/test-utils";
import ExecResult from "../ExecResult.vue";
import axios from "axios";
import DOMPurify from "dompurify";

const routerPushMock = vi.hoisted(() => vi.fn());

vi.mock("axios");

vi.mock("vue-router", () => ({
  useRouter: () => ({ push: routerPushMock }),
}));

vi.mock("markdown-it", () => ({
  __esModule: true,
  default: class MarkdownItMock {
    render(src) {
      return `<p>${src}</p>`;
    }
  },
}));

const flushPromises = () => new Promise((r) => setTimeout(r));

describe("ExecResult.vue", () => {
  beforeEach(() => {
    routerPushMock.mockReset();
  });

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
    axios.get.mockResolvedValueOnce({
      data: { is_authenticated: false },
    });

    mount(ExecResult, {
      global: {
        stubs: { "router-link": true, "router-view": true },
      },
    });

    await flushPromises();
    expect(routerPushMock).toHaveBeenCalledWith("/login");
  });

  it("handles checkAuthStatus error gracefully", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});

    axios.get.mockRejectedValueOnce(new Error("Network error"));

    mount(ExecResult, {
      global: {
        stubs: { "router-link": true, "router-view": true },
      },
    });

    await flushPromises();
    // auth check fails → not authenticated → redirect
    expect(routerPushMock).toHaveBeenCalledWith("/login");
    console.error.mockRestore();
  });

  it("renderedMarkdown returns empty string when source is empty", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
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
    vi.spyOn(console, "error").mockImplementation(() => {});
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
    vi.spyOn(console, "error").mockImplementation(() => {});
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
    const { default: MarkdownIt } = await import("markdown-it");
    const instances = MarkdownIt.mock ? MarkdownIt.mock.instances : null;
    // mock 클래스의 prototype render를 spy로 throw하게 설정
    const renderSpy = vi
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

  it("DOMPurify whitelist blocks script tags from exec_result", async () => {
    // 서버가 XSS 페이로드를 exec_result로 반환하는 시나리오
    axios.get
      .mockResolvedValueOnce({ data: { is_authenticated: true } })
      .mockResolvedValueOnce({
        data: { exec_result: "<script>alert(1)</script><b>정상 텍스트</b>" },
      });

    const wrapper = mount(ExecResult, {
      global: { stubs: { "router-link": true, "router-view": true } },
    });
    await flushPromises();

    const rendered = wrapper.html();
    expect(rendered).not.toContain("<script>");
    expect(rendered).not.toContain("alert(1)");
  });

  it("DOMPurify whitelist blocks event handler attributes", async () => {
    // onerror, onclick 등 이벤트 핸들러 차단
    const raw =
      '<img src="x" onerror="alert(1)"><a href="#" onclick="evil()">link</a>';
    const clean = DOMPurify.sanitize(raw, {
      ALLOWED_TAGS: [
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "div",
        "blockquote",
        "pre",
        "code",
        "ul",
        "ol",
        "li",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "a",
        "strong",
        "em",
        "b",
        "i",
        "del",
        "ins",
        "span",
        "br",
        "hr",
        "img",
      ],
      ALLOWED_ATTR: [
        "href",
        "src",
        "alt",
        "title",
        "class",
        "id",
        "target",
        "rel",
      ],
    });
    expect(clean).not.toContain("onerror");
    expect(clean).not.toContain("onclick");
    expect(clean).toContain("<img");
    expect(clean).toContain("link");
  });

  it("DOMPurify whitelist preserves safe markdown tags", () => {
    const raw =
      "<h1>제목</h1><p>본문</p><a href='https://example.com'>링크</a><code>code</code>";
    const clean = DOMPurify.sanitize(raw, {
      ALLOWED_TAGS: [
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "div",
        "blockquote",
        "pre",
        "code",
        "ul",
        "ol",
        "li",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "a",
        "strong",
        "em",
        "b",
        "i",
        "del",
        "ins",
        "span",
        "br",
        "hr",
        "img",
      ],
      ALLOWED_ATTR: [
        "href",
        "src",
        "alt",
        "title",
        "class",
        "id",
        "target",
        "rel",
      ],
    });
    expect(clean).toContain("<h1>");
    expect(clean).toContain("<p>");
    expect(clean).toContain("https://example.com");
    expect(clean).toContain("<code>");
  });
});
