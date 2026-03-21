import { getApiUrlPath, getCommonHeaders, handleApiError } from "@/utils/api";

describe("utils/api", () => {
  const origEnv = { ...process.env };
  let consoleSpy;

  beforeEach(() => {
    consoleSpy = jest.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    process.env = { ...origEnv };
    consoleSpy.mockRestore();
  });

  it("returns api url from env or default", () => {
    process.env.VUE_APP_API_URL = "https://api.example.com";
    expect(getApiUrlPath()).toBe("https://api.example.com");

    delete process.env.VUE_APP_API_URL;
    expect(getApiUrlPath()).toBe("http://localhost:8000");
  });

  it("returns common headers", () => {
    expect(getCommonHeaders()).toEqual({ "Content-Type": "application/json" });
  });

  it("handleApiError logs details for response/request/message", () => {
    handleApiError({ response: { data: { a: 1 }, status: 400 } }, "ctx");
    handleApiError({ request: {} }, "ctx");
    handleApiError(new Error("boom"), "ctx");
    expect(consoleSpy).toHaveBeenCalled();
  });

  it("handleApiError logs network error when request exists but no response", () => {
    const error = { request: { url: "/test" } };
    handleApiError(error, "network");
    expect(consoleSpy).toHaveBeenCalledWith(
      "No response received:",
      error.request,
    );
  });

  it("handleApiError logs message when neither response nor request exists", () => {
    const error = { message: "Something went wrong" };
    handleApiError(error, "setup");
    expect(consoleSpy).toHaveBeenCalledWith(
      "Error message:",
      "Something went wrong",
    );
  });

  it("handleApiError uses default empty context when not provided", () => {
    const error = new Error("no context");
    handleApiError(error);
    expect(consoleSpy).toHaveBeenCalledWith("API Error :", error);
  });
});
