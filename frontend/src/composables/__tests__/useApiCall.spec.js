import { useApiCall } from "@/composables/useApiCall";
import axios from "axios";

jest.mock("axios");

describe("composables/useApiCall", () => {
  let consoleErrorSpy;

  beforeEach(() => {
    axios.mockReset?.();
    axios.get?.mockReset?.();
    // 테스트 중 console.error 출력 억제
    consoleErrorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    // console.error restore
    consoleErrorSpy?.mockRestore();
  });

  it("calls GET and returns data", async () => {
    axios.mockResolvedValueOnce({ data: { ok: true } });
    const { get, loading, error } = useApiCall();
    const data = await get("/ping");
    expect(data).toEqual({ ok: true });
    expect(loading.value).toBe(false);
    expect(error.value).toBeNull();
  });

  it("throws on failure status and sets error", async () => {
    axios.mockResolvedValueOnce({
      data: { status: "failure", message: "bad" },
    });
    const { get, error } = useApiCall();
    await expect(get("/fail")).rejects.toThrow("bad");
    expect(error.value).toBeTruthy();
  });

  it("supports post/put/delete wrappers", async () => {
    axios.mockResolvedValue({ data: { ok: true } });
    const { post, put, del } = useApiCall();
    await expect(post("/a", { x: 1 })).resolves.toEqual({ ok: true });
    await expect(put("/a", { x: 1 })).resolves.toEqual({ ok: true });
    await expect(del("/a")).resolves.toEqual({ ok: true });
  });

  it("apiCall uses default options when called without options", async () => {
    axios.mockResolvedValueOnce({ data: { ok: true } });
    const { apiCall } = useApiCall();
    const data = await apiCall("/endpoint");
    expect(data).toEqual({ ok: true });
    expect(axios).toHaveBeenCalledWith(
      expect.objectContaining({ method: "GET", withCredentials: true }),
    );
  });

  it("throws default message when failure status has no message", async () => {
    axios.mockResolvedValueOnce({ data: { status: "failure" } });
    const { get, error } = useApiCall();
    await expect(get("/fail")).rejects.toThrow("API call failed");
    expect(error.value).toBeTruthy();
  });

  it("post calls apiCall with post method", async () => {
    axios.mockResolvedValueOnce({ data: { created: true } });
    const { post } = useApiCall();
    const data = await post("/items", { name: "test" });
    expect(data).toEqual({ created: true });
    expect(axios).toHaveBeenCalledWith(
      expect.objectContaining({ method: "POST", data: { name: "test" } }),
    );
  });

  it("put calls apiCall with put method", async () => {
    axios.mockResolvedValueOnce({ data: { updated: true } });
    const { put } = useApiCall();
    const data = await put("/items/1", { name: "updated" });
    expect(data).toEqual({ updated: true });
    expect(axios).toHaveBeenCalledWith(
      expect.objectContaining({ method: "PUT", data: { name: "updated" } }),
    );
  });

  it("del calls apiCall with delete method", async () => {
    axios.mockResolvedValueOnce({ data: { deleted: true } });
    const { del } = useApiCall();
    const data = await del("/items/1");
    expect(data).toEqual({ deleted: true });
    expect(axios).toHaveBeenCalledWith(
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("post uses default empty data when called without data argument", async () => {
    axios.mockResolvedValueOnce({ data: { ok: true } });
    const { post } = useApiCall();
    await post("/endpoint");
    expect(axios).toHaveBeenCalledWith(
      expect.objectContaining({ method: "POST", data: {} }),
    );
  });

  it("put uses default empty data when called without data argument", async () => {
    axios.mockResolvedValueOnce({ data: { ok: true } });
    const { put } = useApiCall();
    await put("/endpoint");
    expect(axios).toHaveBeenCalledWith(
      expect.objectContaining({ method: "PUT", data: {} }),
    );
  });

  it("get uses default empty params when called without params argument", async () => {
    axios.mockResolvedValueOnce({ data: { ok: true } });
    const { get } = useApiCall();
    await get("/endpoint");
    expect(axios).toHaveBeenCalledWith(
      expect.objectContaining({ method: "GET", params: {} }),
    );
  });
});
