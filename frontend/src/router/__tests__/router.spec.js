import router from "@/router";
import axios from "axios";
import { authStore } from "@/stores/authStore";

jest.mock("axios");

describe("router guards", () => {
  let consoleWarnSpy;

  beforeEach(() => {
    axios.get.mockReset();
    authStore.clear();
    // 테스트 중 console.warn 출력 억제
    consoleWarnSpy = jest.spyOn(console, "warn").mockImplementation(() => {});
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
