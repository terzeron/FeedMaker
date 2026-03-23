import { reactive, computed } from "vue";

const PICTURE_KEY = "auth_profile_picture";

const state = reactive({
  isAuthenticated: false,
  userName: null,
  profilePictureUrl: sessionStorage.getItem(PICTURE_KEY) || null,
});

export const authStore = {
  state,

  isLoggedIn: computed(() => state.isAuthenticated),

  setAuthenticated(name, pictureUrl) {
    state.isAuthenticated = true;
    state.userName = name;
    if (pictureUrl) {
      state.profilePictureUrl = pictureUrl;
      sessionStorage.setItem(PICTURE_KEY, pictureUrl);
    }
  },

  updateFromServer(isAuthenticated, name, pictureUrl) {
    state.isAuthenticated = isAuthenticated;
    state.userName = isAuthenticated ? name : null;
    if (isAuthenticated && pictureUrl) {
      state.profilePictureUrl = pictureUrl;
      sessionStorage.setItem(PICTURE_KEY, pictureUrl);
    } else if (!isAuthenticated) {
      state.profilePictureUrl = null;
      sessionStorage.removeItem(PICTURE_KEY);
    }
  },

  clear() {
    state.isAuthenticated = false;
    state.userName = null;
    state.profilePictureUrl = null;
    sessionStorage.removeItem(PICTURE_KEY);
  },
};
