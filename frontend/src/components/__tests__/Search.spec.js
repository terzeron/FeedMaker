import { mount } from "@vue/test-utils";
import Search from "../Search.vue";
import MyButton from "../MyButton.vue";
import axios from "axios";
import DOMPurify from "dompurify";

vi.mock("axios");
axios.isCancel = vi.fn(() => false);

const stubs = {
  "font-awesome-icon": true,
  BButton: { template: "<button><slot /></button>" },
  BContainer: { template: "<div><slot /></div>" },
  BRow: { template: "<div><slot /></div>" },
  BCol: { template: "<div><slot /></div>" },
  BInputGroup: { template: "<div><slot /></div>" },
  BFormInput: { template: "<input />" },
  BInputGroupText: { template: "<div><slot /></div>" },
  BCard: { template: '<div><slot /><slot name="header" /></div>' },
  BCardBody: { template: "<div><slot /></div>" },
  BSpinner: { template: "<span />" },
};

const flushPromises = () => new Promise((r) => setTimeout(r));
const nativeAbortController = global.AbortController;

describe("Search.vue", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    axios.isCancel = vi.fn(() => false);
  });

  afterEach(() => {
    global.AbortController = nativeAbortController;
  });

  it("performs per-site search and renders results", async () => {
    // 1st call: site names
    axios.get.mockResolvedValueOnce({
      data: { status: "success", site_names: ["funbe", "toonkor"] },
    });
    // 2nd call: funbe result
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        search_result: '<div><a href="https://a">제목1</a></div>',
      },
    });
    // 3rd call: toonkor result
    axios.get.mockResolvedValueOnce({
      data: { status: "success", search_result: "" },
    });

    const wrapper = mount(Search, {
      global: { stubs, components: { MyButton } },
    });

    await wrapper.setData({ searchKeyword: "드래곤" });
    await wrapper.vm.search();
    await flushPromises();

    expect(wrapper.vm.siteResults.length).toBe(2);
    expect(wrapper.vm.siteResults[0].name).toBe("funbe");
    expect(wrapper.vm.siteResults[0].status).toBe("success");
    expect(wrapper.vm.siteResults[0].html).toContain("제목1");
    expect(wrapper.vm.siteResults[1].name).toBe("toonkor");
    expect(wrapper.vm.siteResults[1].status).toBe("success");
    expect(wrapper.vm.siteResults[1].html).toBe("");
  });

  it("handles per-site search error", async () => {
    // 1st call: site names
    axios.get.mockResolvedValueOnce({
      data: { status: "success", site_names: ["funbe"] },
    });
    // 2nd call: funbe fails
    axios.get.mockRejectedValueOnce(new Error("network"));

    const wrapper = mount(Search, {
      global: { stubs, components: { MyButton } },
    });

    await wrapper.setData({ searchKeyword: "키워드" });
    await wrapper.vm.search();
    await flushPromises();

    expect(wrapper.vm.siteResults.length).toBe(1);
    expect(wrapper.vm.siteResults[0].status).toBe("error");
    expect(wrapper.vm.siteResults[0].error).toBeTruthy();
  });

  it("aborts previous search when new search starts", async () => {
    const abortSpy = vi.fn();
    global.AbortController = vi.fn(function MockAbortController() {
      this.signal = { aborted: false };
      this.abort = abortSpy;
    });

    // First search: site names (will be aborted)
    let resolveFirst;
    axios.get.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveFirst = resolve;
        }),
    );
    // Second search: site names
    axios.get.mockResolvedValueOnce({
      data: { status: "success", site_names: [] },
    });

    const wrapper = mount(Search, {
      global: { stubs, components: { MyButton } },
    });

    await wrapper.setData({ searchKeyword: "드래곤" });
    // Start first search (won't resolve)
    const p1 = wrapper.vm.search();

    // Start second search - should abort first
    await wrapper.setData({ searchKeyword: "무림" });
    await wrapper.vm.search();
    await flushPromises();

    expect(abortSpy).toHaveBeenCalledTimes(1);
  });

  it("does not search with empty keyword", async () => {
    const wrapper = mount(Search, {
      global: { stubs, components: { MyButton } },
    });

    await wrapper.setData({ searchKeyword: "" });
    await wrapper.vm.search();
    await flushPromises();

    expect(axios.get).not.toHaveBeenCalled();
    expect(wrapper.vm.siteResults.length).toBe(0);
  });

  it("does not search with whitespace-only keyword", async () => {
    const wrapper = mount(Search, {
      global: { stubs, components: { MyButton } },
    });

    await wrapper.setData({ searchKeyword: "   " });
    await wrapper.vm.search();
    await flushPromises();

    expect(axios.get).not.toHaveBeenCalled();
    expect(wrapper.vm.siteResults.length).toBe(0);
  });

  it("handles top-level search error (non-cancel)", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    // site names call rejects with a non-cancel error
    axios.get.mockRejectedValueOnce(new Error("Network Error"));

    const wrapper = mount(Search, {
      global: { stubs, components: { MyButton } },
    });

    await wrapper.setData({ searchKeyword: "드래곤" });
    await wrapper.vm.search();
    await flushPromises();

    expect(console.error).toHaveBeenCalled();
    expect(wrapper.vm.siteResults.length).toBe(0);
    console.error.mockRestore();
  });

  it("handles non-success status from site search", async () => {
    // 1st call: site names
    axios.get.mockResolvedValueOnce({
      data: { status: "success", site_names: ["funbe"] },
    });
    // 2nd call: funbe returns non-success
    axios.get.mockResolvedValueOnce({
      data: { status: "failure", message: "검색 실패" },
    });

    const wrapper = mount(Search, {
      global: { stubs, components: { MyButton } },
    });

    await wrapper.setData({ searchKeyword: "키워드" });
    await wrapper.vm.search();
    await flushPromises();

    expect(wrapper.vm.siteResults[0].status).toBe("error");
    expect(wrapper.vm.siteResults[0].error).toBe("검색 실패");
  });

  it("falls back to default error message when site search has no message", async () => {
    // 1st call: site names
    axios.get.mockResolvedValueOnce({
      data: { status: "success", site_names: ["funbe"] },
    });
    // 2nd call: non-success WITHOUT message → `|| "검색 실패"` 폴백 분기
    axios.get.mockResolvedValueOnce({
      data: { status: "error" },
    });

    const wrapper = mount(Search, {
      global: { stubs, components: { MyButton } },
    });

    await wrapper.setData({ searchKeyword: "키워드" });
    await wrapper.vm.search();
    await flushPromises();

    expect(wrapper.vm.siteResults[0].status).toBe("error");
    expect(wrapper.vm.siteResults[0].error).toBe("검색 실패");
  });

  it("returns early when site names response is not success", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "failure" },
    });

    const wrapper = mount(Search, {
      global: { stubs, components: { MyButton } },
    });

    await wrapper.setData({ searchKeyword: "키워드" });
    await wrapper.vm.search();
    await flushPromises();

    expect(wrapper.vm.siteResults.length).toBe(0);
  });

  it("ignores cancel error in top-level catch", async () => {
    // Make isCancel return true for cancel errors
    axios.isCancel = vi.fn((err) => err && err.__CANCEL__);
    const cancelError = { __CANCEL__: true, message: "canceled" };
    axios.get.mockRejectedValueOnce(cancelError);

    const wrapper = mount(Search, {
      global: { stubs, components: { MyButton } },
    });

    await wrapper.setData({ searchKeyword: "드래곤" });
    await wrapper.vm.search();
    await flushPromises();

    // Should not log error for cancel
    expect(wrapper.vm.siteResults.length).toBe(0);
  });

  it("renders site result cards with all status variants", async () => {
    const wrapper = mount(Search, {
      global: { stubs, components: { MyButton } },
    });

    // Manually set siteResults with all status variants to trigger template branches
    wrapper.vm.siteResults = [
      { name: "site1", status: "loading", html: "", error: "" },
      {
        name: "site2",
        status: "success",
        html: "<div>result</div>",
        error: "",
      },
      { name: "site3", status: "success", html: "", error: "" },
      { name: "site4", status: "error", html: "", error: "검색 실패" },
    ];
    await flushPromises();

    const html = wrapper.html();
    expect(html).toContain("site1");
    expect(html).toContain("site2");
    expect(html).toContain("site3");
    expect(html).toContain("site4");
    expect(html).toContain("검색 실패");
  });

  it("binds v-model and renders default slot on the search input", async () => {
    // 기본 BFormInput 스텁(<input />)은 modelValue 바인딩도 슬롯도 렌더링하지 않아
    // v-model의 update 핸들러(setter)와 {{ searchKeyword }} 슬롯이 미커버 상태였다.
    // modelValue를 바인딩하고 슬롯을 렌더링하는 스텁으로 두 경로를 모두 탄다.
    const richStubs = {
      ...stubs,
      BFormInput: {
        props: ["modelValue"],
        emits: ["update:modelValue"],
        template:
          '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" /><span class="slot-content"><slot /></span>',
      },
    };

    const wrapper = mount(Search, {
      global: { stubs: richStubs, components: { MyButton } },
    });

    await wrapper.setData({ searchKeyword: "초기값" });
    // 슬롯 {{ searchKeyword }}가 렌더링되는지 확인 (line 13)
    expect(wrapper.find(".slot-content").text()).toBe("초기값");

    // input에 값을 넣어 update:modelValue를 발생시켜 v-model setter를 탄다 (line 8)
    await wrapper.find("input").setValue("새검색어");
    expect(wrapper.vm.searchKeyword).toBe("새검색어");
    expect(wrapper.find(".slot-content").text()).toBe("새검색어");
  });

  it("mounted hook executes without error", () => {
    const wrapper = mount(Search, {
      global: { stubs, components: { MyButton } },
    });
    // mounted is a no-op but should be covered
    expect(wrapper.exists()).toBe(true);
  });

  it("blocks script tags via DOMPurify whitelist", async () => {
    // 공격자가 제어하는 서버가 XSS 페이로드를 search_result로 반환하는 시나리오
    axios.get.mockResolvedValueOnce({
      data: { status: "success", site_names: ["evil"] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        search_result:
          '<a href="ok">링크</a><script>alert(1)</script><img src="x" onerror="alert(2)">',
      },
    });

    const wrapper = mount(Search, {
      global: { stubs, components: { MyButton } },
    });
    await wrapper.setData({ searchKeyword: "test" });
    await wrapper.vm.search();
    await flushPromises();

    const html = wrapper.vm.siteResults[0]?.html || "";
    expect(html).not.toContain("<script>");
    expect(html).not.toContain("onerror");
    expect(html).toContain("링크"); // 정상 텍스트는 보존
  });

  it("allows safe tags through DOMPurify whitelist", () => {
    const raw =
      '<div><a href="https://example.com">제목</a><b>굵게</b><img src="x.jpg" alt="img"></div>';
    const clean = DOMPurify.sanitize(raw, {
      ALLOWED_TAGS: [
        "a",
        "b",
        "i",
        "em",
        "strong",
        "span",
        "div",
        "p",
        "br",
        "ul",
        "ol",
        "li",
        "img",
      ],
      ALLOWED_ATTR: ["href", "src", "alt", "title", "class", "target", "rel"],
    });
    expect(clean).toContain('<a href="https://example.com">');
    expect(clean).toContain("<b>굵게</b>");
    expect(clean).toContain('<img src="x.jpg"');
  });

  it("ignores cancel error in per-site catch", async () => {
    axios.isCancel = vi.fn((err) => err && err.__CANCEL__);
    // 1st call: site names success
    axios.get.mockResolvedValueOnce({
      data: { status: "success", site_names: ["funbe"] },
    });
    // 2nd call: per-site search is cancelled
    const cancelError = { __CANCEL__: true, message: "canceled" };
    axios.get.mockRejectedValueOnce(cancelError);

    const wrapper = mount(Search, {
      global: { stubs, components: { MyButton } },
    });

    await wrapper.setData({ searchKeyword: "드래곤" });
    await wrapper.vm.search();
    await flushPromises();

    // Cancel error should be ignored, site result should stay in initial state
    expect(wrapper.vm.siteResults.length).toBe(1);
    expect(wrapper.vm.siteResults[0].status).toBe("loading");
  });
});
