import router from "@/router";
import axios from "axios";
import { authStore } from "@/stores/authStore";

vi.mock("axios");

describe("router guards", () => {
  let consoleWarnSpy;

  beforeEach(() => {
    axios.get.mockReset();
    authStore.clear();
    // 테스트 중 console.warn 출력 억제
    consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
  });

  afterEach(() => {
    // console.warn restore
    consoleWarnSpy?.mockRestore();
  });

  it("allows navigation when authenticated", async () => {
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: true } });
    await router.push("/result");
    expect(router.currentRoute.value.path).toBe("/result");
  });

  it("redirects to login when unauthenticated", async () => {
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: false } });
    await router.push("/problems");
    expect(router.currentRoute.value.path).toBe("/login");
  });

  it("does not call the auth API for public routes", async () => {
    await router.push("/login");
    expect(router.currentRoute.value.path).toBe("/login");
    expect(axios.get).not.toHaveBeenCalled();
  });

  it("redirects / to /result", async () => {
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: true } });
    await router.push("/");
    expect(router.currentRoute.value.path).toBe("/result");
  });

  it("keeps the original destination in the redirect query", async () => {
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: false } });
    await router.push("/management/g1/f1?x=1");
    expect(router.currentRoute.value.path).toBe("/login");
    expect(router.currentRoute.value.query.redirect).toBe(
      "/management/g1/f1?x=1",
    );
  });

  it("clears stale localStorage auth data when unauthenticated", async () => {
    ["is_authorized", "access_token", "name", "session_expiry"].forEach((k) =>
      localStorage.setItem(k, "stale"),
    );
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: false } });
    await router.push("/search");
    ["is_authorized", "access_token", "name", "session_expiry"].forEach((k) =>
      expect(localStorage.getItem(k)).toBeNull(),
    );
  });

  it("treats an auth API error as unauthenticated", async () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    axios.get.mockRejectedValueOnce(new Error("boom"));
    await router.push("/problems");
    expect(router.currentRoute.value.path).toBe("/login");
    expect(errorSpy).toHaveBeenCalled();
    errorSpy.mockRestore();
  });

  it("passes route params to the FeedManagement route when authenticated", async () => {
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: true } });
    await router.push("/management/g1/f1");
    expect(router.currentRoute.value.name).toBe("FeedManagementWithParams");
    expect(router.currentRoute.value.params).toEqual({
      group: "g1",
      feed: "f1",
    });
  });

  it("restores profile picture url from server response", async () => {
    axios.get.mockResolvedValueOnce({
      data: {
        is_authenticated: true,
        name: "User",
        profile_picture_url: "https://example.com/pic.jpg",
      },
    });
    await router.push("/result");
    expect(authStore.state.profilePictureUrl).toBe(
      "https://example.com/pic.jpg",
    );
  });
});
