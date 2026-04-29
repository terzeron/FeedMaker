import { useAuth } from "@/composables/useAuth";
import axios from "axios";

const mockPush = jest.fn();
jest.mock("axios");
jest.mock("vue-router", () => ({
  useRouter: () => ({ push: mockPush }),
}));

describe("composables/useAuth", () => {
  beforeEach(() => {
    axios.get.mockReset();
    axios.post.mockReset();
    mockPush.mockReset();
    localStorage.clear();
  });

  describe("checkAuth", () => {
    it("sets authorized state when authenticated", async () => {
      axios.get.mockResolvedValueOnce({
        data: { is_authenticated: true, name: "User" },
      });
      const { checkAuth, isAuthorized, userName } = useAuth();
      await expect(checkAuth()).resolves.toBe(true);
      expect(isAuthorized.value).toBe(true);
      expect(userName.value).toBe("User");
    });

    it("sets unauthorized state when not authenticated", async () => {
      axios.get.mockResolvedValueOnce({ data: { is_authenticated: false } });
      const { checkAuth, isAuthorized, userName } = useAuth();
      const result = await checkAuth();
      expect(result).toBe(false);
      expect(isAuthorized.value).toBe(false);
      expect(userName.value).toBeNull();
    });

    it("handles API error gracefully", async () => {
      axios.get.mockRejectedValueOnce(new Error("Network Error"));
      const consoleErrorSpy = jest
        .spyOn(console, "error")
        .mockImplementation(() => {});
      const { checkAuth, isAuthorized, userName } = useAuth();
      const result = await checkAuth();
      expect(result).toBe(false);
      expect(isAuthorized.value).toBe(false);
      expect(userName.value).toBeNull();
      consoleErrorSpy.mockRestore();
    });
  });

  describe("requireAuth", () => {
    it("returns true when authenticated", async () => {
      axios.get.mockResolvedValueOnce({
        data: { is_authenticated: true, name: "User" },
      });
      const { requireAuth } = useAuth();
      const result = await requireAuth();
      expect(result).toBe(true);
      expect(mockPush).not.toHaveBeenCalled();
    });

    it("redirects to login when not authenticated", async () => {
      axios.get.mockResolvedValueOnce({ data: { is_authenticated: false } });
      const { requireAuth } = useAuth();
      const result = await requireAuth();
      expect(result).toBe(false);
      expect(mockPush).toHaveBeenCalledWith("/login");
    });
  });

  describe("logout", () => {
    it("clears state and calls API", async () => {
      axios.post.mockResolvedValueOnce({});
      const { logout, isAuthorized, userName } = useAuth();
      await logout();
      expect(axios.post).toHaveBeenCalled();
      expect(isAuthorized.value).toBe(false);
      expect(userName.value).toBeNull();
      expect(mockPush).toHaveBeenCalledWith("/login");
    });

    it("clears state even when API fails", async () => {
      axios.post.mockRejectedValueOnce(new Error("Logout failed"));
      const consoleErrorSpy = jest
        .spyOn(console, "error")
        .mockImplementation(() => {});
      const { logout, isAuthorized, userName } = useAuth();
      await logout();
      expect(isAuthorized.value).toBe(false);
      expect(userName.value).toBeNull();
      expect(mockPush).toHaveBeenCalledWith("/login");
      consoleErrorSpy.mockRestore();
    });

    it("removes legacy localStorage items", async () => {
      localStorage.setItem("access_token", "token");
      localStorage.setItem("name", "User");
      localStorage.setItem("is_authorized", "true");
      localStorage.setItem("session_expiry", "123");
      axios.post.mockResolvedValueOnce({});
      const { logout } = useAuth();
      await logout();
      expect(localStorage.getItem("access_token")).toBeNull();
      expect(localStorage.getItem("name")).toBeNull();
      expect(localStorage.getItem("is_authorized")).toBeNull();
      expect(localStorage.getItem("session_expiry")).toBeNull();
    });
  });

  describe("redirectToLogin", () => {
    it("navigates to /login", () => {
      const { redirectToLogin } = useAuth();
      redirectToLogin();
      expect(mockPush).toHaveBeenCalledWith("/login");
    });
  });

  describe("deprecated functions", () => {
    it("clearSessionData clears state and localStorage", () => {
      const consoleWarnSpy = jest
        .spyOn(console, "warn")
        .mockImplementation(() => {});
      localStorage.setItem("access_token", "token");
      localStorage.setItem("name", "User");
      localStorage.setItem("is_authorized", "true");
      localStorage.setItem("session_expiry", "123");
      const { clearSessionData, isAuthorized, userName } = useAuth();
      clearSessionData();
      expect(isAuthorized.value).toBe(false);
      expect(userName.value).toBeNull();
      expect(localStorage.getItem("access_token")).toBeNull();
      expect(localStorage.getItem("name")).toBeNull();
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining("deprecated"),
      );
      consoleWarnSpy.mockRestore();
    });

    it("checkSessionExpiry returns true and warns", () => {
      const consoleWarnSpy = jest
        .spyOn(console, "warn")
        .mockImplementation(() => {});
      const { checkSessionExpiry } = useAuth();
      expect(checkSessionExpiry()).toBe(true);
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining("deprecated"),
      );
      consoleWarnSpy.mockRestore();
    });

    it("setAuth warns about deprecation", () => {
      const consoleWarnSpy = jest
        .spyOn(console, "warn")
        .mockImplementation(() => {});
      const { setAuth } = useAuth();
      setAuth();
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining("deprecated"),
      );
      consoleWarnSpy.mockRestore();
    });
  });

  describe("computed", () => {
    it("isLoggedIn reflects isAuthorized", async () => {
      axios.get.mockResolvedValueOnce({
        data: { is_authenticated: true, name: "User" },
      });
      const { checkAuth, isLoggedIn } = useAuth();
      expect(isLoggedIn.value).toBe(false);
      await checkAuth();
      expect(isLoggedIn.value).toBe(true);
    });
  });

  describe("checkAuth name fallback", () => {
    it("sets userName to null when name is null", async () => {
      axios.get.mockResolvedValueOnce({
        data: { is_authenticated: true, name: null },
      });
      const { checkAuth, isAuthorized, userName } = useAuth();
      await checkAuth();
      expect(isAuthorized.value).toBe(true);
      expect(userName.value).toBeNull();
    });

    it("sets userName to null when name is undefined", async () => {
      axios.get.mockResolvedValueOnce({ data: { is_authenticated: true } });
      const { checkAuth, isAuthorized, userName } = useAuth();
      await checkAuth();
      expect(isAuthorized.value).toBe(true);
      expect(userName.value).toBeNull();
    });
  });

  describe("GET /auth/me — contract compliance", () => {
    it("reads is_authenticated, name from the full authenticated response shape", async () => {
      // backend /auth/me 인증 응답의 완전한 shape: {is_authenticated, email, name, profile_picture_url}
      // backend/main.py get_me() 와 동기화 필요
      axios.get.mockResolvedValueOnce({
        data: {
          is_authenticated: true,
          email: "user@example.com",
          name: "Contract User",
          profile_picture_url: "https://example.com/pic.jpg",
        },
      });
      const { checkAuth, isAuthorized, userName } = useAuth();
      await checkAuth();
      expect(isAuthorized.value).toBe(true);
      expect(userName.value).toBe("Contract User");
    });

    it("handles unauthenticated response shape {is_authenticated: false} only", async () => {
      // backend /auth/me 비인증 응답의 완전한 shape: {is_authenticated}
      axios.get.mockResolvedValueOnce({
        data: { is_authenticated: false },
      });
      const { checkAuth, isAuthorized, userName } = useAuth();
      await checkAuth();
      expect(isAuthorized.value).toBe(false);
      expect(userName.value).toBeNull();
    });
  });
});
