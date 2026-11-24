import { flushPromises, mount } from "@vue/test-utils";
import Problems from "../Problems.vue";
import axios from "axios";

vi.mock("axios");

const stubs = Object.fromEntries(
  ["router-link", "BContainer", "BRow", "BCol", "BCardHeader", "BCardBody", "BModal"]
    .map((name) => [name, { template: "<div><slot /></div>" }]),
);
stubs["font-awesome-icon"] = true;

const feed = (name, running, ratio) => ({
  group_name: "group", feed_name: name, feed_title: name,
  running_status: running, progress_ratio: ratio,
  html_file_count: ratio, total_item_count: 100,
});

describe("Problems progress polling", () => {
  let wrapper;
  let progressGet;
  let errorSpy;
  const table = () => wrapper.findAll("table")[1];

  beforeEach(() => {
    vi.useFakeTimers();
    errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    progressGet = vi.fn().mockResolvedValue({ data: {
      status: "success", result: { a: feed("a", true, 20), b: feed("b", false, 10) },
    } });
    axios.get.mockImplementation((url, options) => url.endsWith("/problems/progress_info")
      ? progressGet(options)
      : Promise.resolve({ data: { status: "success", result: [] } }));
    wrapper = mount(Problems, { global: { stubs } });
  });

  afterEach(() => {
    wrapper.unmount();
    vi.useRealTimers();
    errorSpy.mockRestore();
  });

  it("refreshes only progress every 10 seconds and retains rows while waiting", async () => {
    await flushPromises();
    const firstRow = table().findAll("tbody tr")[0].element;
    expect(table().findAll("td")[0].classes()).toContain("progress-running-title");
    expect(table().findAll("tbody tr")[1].find("td").classes()).not.toContain("progress-running-title");
    let finish;
    progressGet.mockReturnValueOnce(new Promise((resolve) => {
 finish = resolve; 
}));
    const initialRequestCount = axios.get.mock.calls.length;

    await vi.advanceTimersByTimeAsync(9999);
    expect(progressGet).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(progressGet).toHaveBeenCalledTimes(2);
    expect(axios.get.mock.calls.length).toBe(initialRequestCount + 1);
    expect(table().findAll("tbody tr")[0].element).toBe(firstRow);
    expect(table().text()).toContain("20 / 100");

    await vi.advanceTimersByTimeAsync(10000);
    expect(progressGet).toHaveBeenCalledTimes(2);
    finish({ data: { status: "success", result: [feed("a", false, 5), feed("b", true, 30)] } });
    await flushPromises();
    expect(table().findAll("tbody tr")[1].element).toBe(firstRow);
    expect(table().findAll("tbody tr")[1].find("td").classes()).not.toContain("progress-running-title");
    expect(table().findAll("tbody tr")[0].find("td").classes()).toContain("progress-running-title");
    expect(table().text()).toContain("30 / 100");
  });

  it("keeps data after failures and retries, accepting a successful empty result", async () => {
    await flushPromises();
    progressGet.mockRejectedValueOnce(new Error("offline"));
    await vi.advanceTimersByTimeAsync(10000);
    expect(table().findAll("tbody tr")).toHaveLength(2);
    progressGet.mockResolvedValueOnce({ data: { status: "failure" } });
    await vi.advanceTimersByTimeAsync(10000);
    expect(table().findAll("tbody tr")).toHaveLength(2);
    progressGet.mockResolvedValueOnce({ data: { status: "success", result: [] } });
    await vi.advanceTimersByTimeAsync(10000);
    expect(table().findAll("tbody tr")).toHaveLength(0);
  });

  it("stops polling and cancels the pending request when leaving the tab", async () => {
    await flushPromises();
    let finish;
    progressGet.mockReturnValueOnce(new Promise((resolve) => {
 finish = resolve; 
}));
    await vi.advanceTimersByTimeAsync(10000);
    const { signal } = progressGet.mock.calls[1][0];
    const vm = wrapper.vm;
    wrapper.unmount();
    expect(signal.aborted).toBe(true);
    finish({ data: { status: "success", result: [] } });
    await flushPromises();
    expect(vm.progressInfolist).toHaveLength(2);
    await vi.advanceTimersByTimeAsync(30000);
    expect(progressGet).toHaveBeenCalledTimes(2);
  });
});
