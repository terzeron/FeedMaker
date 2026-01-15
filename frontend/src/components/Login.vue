<template>
  <div class="container-fluid">
    <div class="row">
      <div class="col-12">
        <div id="facebookAuthView">
          <div>
            <FacebookAuth @auth-initialized="authInitialized" ref="authRef" />
            <div>
              <div v-if="name">
                <p>{{ name }}님으로 로그인하였습니다.</p>
              </div>
              <button
                class="btn btn-outline-primary"
                v-if="is_logged"
                href="#"
                @click="logout()"
              >
                페이스북 로그아웃
                <font-awesome-icon :icon="['fab', 'facebook']" />
              </button>
              <button class="btn btn-outline-primary" v-else href="#" @click="login">
                페이스북 로그인
                <font-awesome-icon :icon="['fab', 'facebook']" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style></style>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";
import FacebookAuth from "./FacebookAuth.vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faFacebook } from "@fortawesome/free-brands-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { getApiUrlPath } from "../utils/api";

// Define component name for ESLint
defineOptions({
  name: "UserLogin",
});

library.add(faFacebook);

const router = useRouter();
const authRef = ref(null);

const initialized = ref(false);
const accessToken = ref(null);
const status = ref(null);
const profile = ref(null);

// 세션 정보는 이제 서버에서 관리 (httpOnly 쿠키)
const userName = ref(null);
const isAuthenticated = ref(false);

const is_logged = computed(() => {
  return isAuthenticated.value;
});

const name = computed(() => {
  return userName.value;
});

const authInitialized = () => {
  initialized.value = true;
};

const login = async () => {
  if (isAuthenticated.value) {
    await router.push("/result");
    return;
  }

  // Facebook SDK 초기화 상태 확인
  const isFacebookReady = initialized.value && authRef.value && authRef.value.isInitialized?.();

  if (!isFacebookReady) {
    console.error("Facebook Auth is not initialized. Please wait...");
    alert("Facebook Auth가 아직 초기화되지 않았습니다. 잠시 후 다시 시도해주세요.");
    return;
  }

  if (!authRef.value) {
    console.error("AuthRef is not available");
    alert("Facebook Auth 참조를 찾을 수 없습니다.");
    return;
  }

  try {
    accessToken.value = await authRef.value.login();
    profile.value = await authRef.value.getProfile();

    if (!profile.value || !profile.value["email"] || !profile.value["name"]) {
      alert("프로필 정보를 가져올 수 없습니다.");
      return;
    }

    // 백엔드로 로그인 요청 (세션 생성 및 httpOnly 쿠키 설정)
    const response = await axios.post(
      `${getApiUrlPath()}/auth/login`,
      {
        email: profile.value["email"],
        name: profile.value["name"],
        access_token: accessToken.value
      },
      {
        withCredentials: true  // 쿠키 포함
      }
    );

    if (response.data.status === "success") {
      // 로그인 성공 - 서버가 httpOnly 쿠키 설정함
      userName.value = profile.value["name"];
      isAuthenticated.value = true;

      // CSRF 토큰을 localStorage에 저장 (cross-origin 쿠키 접근 제한 우회)
      if (response.data.csrf_token) {
        localStorage.setItem("csrf_token", response.data.csrf_token);
      }

      await router.push("/result");
    } else {
      alert(response.data.message || "로그인 실패");
    }
  } catch (error) {
    console.error("Login error:", error);
    if (error.response?.status === 403) {
      alert("허용되지 않은 이메일입니다.");
    } else {
      alert("로그인 중 오류가 발생했습니다: " + (error.response?.data?.detail || error.message));
    }
  }
};

const logout = async () => {
  try {
    // 백엔드로 로그아웃 요청 (세션 삭제 및 httpOnly 쿠키 제거)
    await axios.post(
      `${getApiUrlPath()}/auth/logout`,
      {},
      {
        withCredentials: true  // 쿠키 포함
      }
    );

    // 로컬 상태 초기화
    userName.value = null;
    isAuthenticated.value = false;

    // Facebook 로그아웃
    if (authRef.value) {
      await authRef.value.logout();
    }

    // 기존 localStorage 데이터 정리 (마이그레이션용)
    localStorage.removeItem("access_token");
    localStorage.removeItem("name");
    localStorage.removeItem("is_authorized");
    localStorage.removeItem("session_expiry");
    localStorage.removeItem("csrf_token");  // CSRF 토큰 제거
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("name");
    sessionStorage.removeItem("is_authorized");

    await router.push("/result");
  } catch (error) {
    console.error("Logout error:", error);
    alert("로그아웃 중 오류가 발생했습니다: " + error.message);
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
      userName.value = response.data.name;
      isAuthenticated.value = true;
    } else {
      userName.value = null;
      isAuthenticated.value = false;
    }
  } catch (error) {
    console.error("Auth status check error:", error);
    userName.value = null;
    isAuthenticated.value = false;
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
