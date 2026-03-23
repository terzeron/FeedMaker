<template>
  <div class="login-wrapper">
    <div class="login-card">
      <FacebookAuth @auth-initialized="authInitialized" @auth-error="authFailed" ref="authRef" />
      <h5 class="login-title">FeedMaker</h5>
      <div v-if="name" class="login-greeting">
        {{ name }}님으로 로그인하였습니다.
      </div>
      <!-- SDK 로딩 중 -->
      <div v-if="!initialized && !sdkFailed" class="text-muted">
        <div class="spinner-border spinner-border-sm me-2" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        로그인 준비 중...
      </div>
      <!-- SDK 로드 실패 -->
      <div v-else-if="sdkFailed" class="text-danger text-center">
        <p class="mb-2">Facebook 로그인을 불러올 수 없습니다.</p>
        <button class="btn btn-outline-secondary btn-sm" @click="retrySdk">
          <font-awesome-icon :icon="['fa', 'rotate-right']" class="me-1" />
          다시 시도
        </button>
      </div>
      <!-- 로그아웃 버튼 -->
      <button
        v-else-if="is_logged"
        class="btn btn-outline-secondary w-100"
        :disabled="logoutLoading"
        @click="logout()"
      >
        <span v-if="logoutLoading" class="spinner-border spinner-border-sm me-1" role="status" />
        <font-awesome-icon :icon="['fab', 'facebook']" class="me-1" />
        로그아웃
      </button>
      <!-- 로그인 버튼 -->
      <button
        v-else
        class="btn btn-facebook w-100"
        :disabled="loginLoading"
        @click="login"
      >
        <span v-if="loginLoading" class="spinner-border spinner-border-sm me-1" role="status" />
        <font-awesome-icon :icon="['fab', 'facebook']" class="me-1" />
        Facebook으로 로그인
      </button>
    </div>
    <ToastNotification :notification="notification" @hide="hideNotification" />
  </div>
</template>

<style scoped>
.login-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 56px);
  background-color: #f5f5f5;
}

.login-card {
  width: 100%;
  max-width: 360px;
  padding: 2rem;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.login-title {
  margin-bottom: 1.5rem;
  font-weight: 600;
  color: #333;
}

.login-greeting {
  margin-bottom: 1rem;
  color: #495057;
}

.btn-facebook {
  background-color: #1877f2;
  border-color: #1877f2;
  color: #fff;
}

.btn-facebook:hover:not(:disabled) {
  background-color: #166fe5;
  border-color: #166fe5;
  color: #fff;
}

.btn-facebook:disabled {
  opacity: 0.7;
}
</style>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";
import FacebookAuth from "./FacebookAuth.vue";
import ToastNotification from "./ToastNotification.vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faFacebook } from "@fortawesome/free-brands-svg-icons";
import { faRotateRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { getApiUrlPath } from "../utils/api";
import { useNotification } from "../composables/useNotification";
import { authStore } from "../stores/authStore";

// Define component name for ESLint
defineOptions({
  name: "UserLogin",
});

library.add(faFacebook, faRotateRight);

const router = useRouter();
const { notification, showError, showWarning, hideNotification } = useNotification();
const authRef = ref(null);

const initialized = ref(false);
const sdkFailed = ref(false);
const loginLoading = ref(false);
const logoutLoading = ref(false);
const accessToken = ref(null);
const status = ref(null);
const profile = ref(null);

const is_logged = computed(() => {
  return authStore.state.isAuthenticated;
});

const name = computed(() => {
  return authStore.state.userName;
});

const authInitialized = () => {
  initialized.value = true;
  sdkFailed.value = false;
};

const authFailed = () => {
  sdkFailed.value = true;
};

const retrySdk = async () => {
  sdkFailed.value = false;
  initialized.value = false;
  if (authRef.value) {
    await authRef.value.retryLoadSDK();
  }
};

const login = async () => {
  if (authStore.state.isAuthenticated) {
    await router.push("/result");
    return;
  }

  // Facebook SDK 초기화 상태 확인
  const isFacebookReady = initialized.value && authRef.value && authRef.value.isInitialized?.();

  if (!isFacebookReady) {
    console.error("Facebook Auth is not initialized. Please wait...");
    showWarning("Facebook Auth가 아직 초기화되지 않았습니다. 잠시 후 다시 시도해주세요.");
    return;
  }

  if (!authRef.value) {
    console.error("AuthRef is not available");
    showError("Facebook Auth 참조를 찾을 수 없습니다.");
    return;
  }

  loginLoading.value = true;
  try {
    accessToken.value = await authRef.value.login();
    profile.value = await authRef.value.getProfile();

    if (!profile.value || !profile.value["email"] || !profile.value["name"]) {
      showError("프로필 정보를 가져올 수 없습니다.");
      return;
    }

    // 백엔드로 로그인 요청 (세션 생성 및 httpOnly 쿠키 설정)
    const pictureUrl = profile.value?.picture?.data?.url || null;
    const response = await axios.post(
      `${getApiUrlPath()}/auth/login`,
      {
        email: profile.value["email"],
        name: profile.value["name"],
        access_token: accessToken.value,
        profile_picture_url: pictureUrl
      },
      {
        withCredentials: true  // 쿠키 포함
      }
    );

    if (response.data.status === "success") {
      // 로그인 성공 - 서버가 httpOnly 쿠키 설정함 (SameSite=Lax로 CSRF 방어)
      authStore.setAuthenticated(profile.value["name"], pictureUrl);
      await router.push("/result");
    } else {
      showError(response.data.message || "로그인 실패");
    }
  } catch (error) {
    console.error("Login error:", error);
    if (error.response?.status === 403) {
      showError("허용되지 않은 이메일입니다.");
    } else {
      showError("로그인 중 오류가 발생했습니다: " + (error.response?.data?.detail || error.message));
    }
  } finally {
    loginLoading.value = false;
  }
};

const logout = async () => {
  logoutLoading.value = true;
  try {
    // 백엔드로 로그아웃 요청 (세션 삭제 및 httpOnly 쿠키 제거)
    await axios.post(
      `${getApiUrlPath()}/auth/logout`,
      {},
      {
        withCredentials: true  // 쿠키 포함
      }
    );

    authStore.clear();

    // Facebook 로그아웃
    if (authRef.value) {
      await authRef.value.logout();
    }

    // 기존 localStorage 데이터 정리 (마이그레이션용)
    localStorage.removeItem("access_token");
    localStorage.removeItem("name");
    localStorage.removeItem("is_authorized");
    localStorage.removeItem("session_expiry");
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("name");
    sessionStorage.removeItem("is_authorized");

    await router.push("/login");
  } catch (error) {
    console.error("Logout error:", error);
    showError("로그아웃 중 오류가 발생했습니다: " + error.message);
  } finally {
    logoutLoading.value = false;
  }
};

// 세션 상태 확인 (페이지 로드 시)
const checkAuthStatus = async () => {
  try {
    const response = await axios.get(
      `${getApiUrlPath()}/auth/me`,
      {
        withCredentials: true  // 쿠키 포함
      }
    );

    if (response.data.is_authenticated) {
      authStore.updateFromServer(true, response.data.name);
    } else {
      authStore.updateFromServer(false, null);
    }
  } catch (error) {
    console.error("Auth status check error:", error);
    authStore.updateFromServer(false, null);
  }
};

onMounted(async () => {
  // 기존 localStorage 데이터 정리 (보안 취약점 제거)
  localStorage.removeItem("access_token");
  localStorage.removeItem("name");
  localStorage.removeItem("is_authorized");
  localStorage.removeItem("session_expiry");
  sessionStorage.removeItem("access_token");
  sessionStorage.removeItem("name");
  sessionStorage.removeItem("is_authorized");

  // 서버에서 세션 상태 확인
  await checkAuthStatus();
});
</script>
