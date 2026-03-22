import { mount } from "@vue/test-utils";
import Search from "../Search.vue";
import MyButton from "../MyButton.vue";
import axios from "axios";

jest.mock("axios");
axios.isCancel = jest.fn(() => false);

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

describe("Search.vue", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    axios.isCancel = jest.fn(() => false);
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
    const abortSpy = jest.fn();
    global.AbortController = jest.fn(() => ({
      signal: { aborted: false },
      abort: abortSpy,
    }));

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
    jest.spyOn(console, "error").mockImplementation(() => {});
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
    axios.isCancel = jest.fn((err) => err && err.__CANCEL__);
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

  it("mounted hook executes without error", () => {
    const wrapper = mount(Search, {
      global: { stubs, components: { MyButton } },
    });
    // mounted is a no-op but should be covered
    expect(wrapper.exists()).toBe(true);
  });

  it("ignores cancel error in per-site catch", async () => {
    axios.isCancel = jest.fn((err) => err && err.__CANCEL__);
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
