import { authStore } from "@/stores/authStore";

describe("stores/authStore", () => {
  beforeEach(() => {
    authStore.clear();
    sessionStorage.clear();
  });

  describe("isLoggedIn", () => {
    it("returns false when not authenticated", () => {
      expect(authStore.isLoggedIn.value).toBe(false);
    });

    it("returns true when authenticated", () => {
      authStore.setAuthenticated("User", null);
      expect(authStore.isLoggedIn.value).toBe(true);
    });
  });

  describe("setAuthenticated", () => {
    it("saves pictureUrl to sessionStorage when provided", () => {
      authStore.setAuthenticated("User", "https://example.com/pic.jpg");
      expect(authStore.state.isAuthenticated).toBe(true);
      expect(authStore.state.userName).toBe("User");
      expect(authStore.state.profilePictureUrl).toBe(
        "https://example.com/pic.jpg",
      );
      expect(sessionStorage.getItem("auth_profile_picture")).toBe(
        "https://example.com/pic.jpg",
      );
    });

    it("does not save to sessionStorage when pictureUrl is falsy", () => {
      authStore.setAuthenticated("User", null);
      expect(authStore.state.isAuthenticated).toBe(true);
      expect(authStore.state.userName).toBe("User");
      expect(authStore.state.profilePictureUrl).toBeNull();
      expect(sessionStorage.getItem("auth_profile_picture")).toBeNull();
    });

    it("does not save to sessionStorage when pictureUrl is undefined", () => {
      authStore.setAuthenticated("User");
      expect(authStore.state.profilePictureUrl).toBeNull();
      expect(sessionStorage.getItem("auth_profile_picture")).toBeNull();
    });
  });

  describe("updateFromServer", () => {
    it("clears profilePictureUrl when not authenticated", () => {
      authStore.setAuthenticated("User", "https://example.com/pic.jpg");
      authStore.updateFromServer(false, null);
      expect(authStore.state.isAuthenticated).toBe(false);
      expect(authStore.state.userName).toBeNull();
      expect(authStore.state.profilePictureUrl).toBeNull();
      expect(sessionStorage.getItem("auth_profile_picture")).toBeNull();
    });

    it("keeps profilePictureUrl when authenticated", () => {
      authStore.setAuthenticated("User", "https://example.com/pic.jpg");
      authStore.updateFromServer(true, "User");
      expect(authStore.state.isAuthenticated).toBe(true);
      expect(authStore.state.userName).toBe("User");
      expect(authStore.state.profilePictureUrl).toBe(
        "https://example.com/pic.jpg",
      );
    });
  });

  describe("clear", () => {
    it("resets all state and removes sessionStorage", () => {
      authStore.setAuthenticated("User", "https://example.com/pic.jpg");
      authStore.clear();
      expect(authStore.state.isAuthenticated).toBe(false);
      expect(authStore.state.userName).toBeNull();
      expect(authStore.state.profilePictureUrl).toBeNull();
      expect(sessionStorage.getItem("auth_profile_picture")).toBeNull();
    });
  });
});
