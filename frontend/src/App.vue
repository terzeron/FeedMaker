<template>
  <div id="app">
    <nav class="navbar navbar-expand-sm navbar-dark bg-secondary">
      <div class="container-fluid">
        <a class="navbar-brand" href="#">FeedMaker</a>
        
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#nav-collapse" aria-controls="nav-collapse" aria-expanded="false" aria-label="Toggle navigation">
          <span class="navbar-toggler-icon"></span>
        </button>
        
        <div class="collapse navbar-collapse" id="nav-collapse">
          <ul class="navbar-nav me-auto">
            <li class="nav-item">
              <router-link to="/result" class="nav-link">실행 결과</router-link>
            </li>
            <li class="nav-item">
              <router-link to="/problems" class="nav-link">문제점과 상태</router-link>
            </li>
            <li class="nav-item">
              <router-link to="/management" class="nav-link">피드 관리</router-link>
            </li>
            <li class="nav-item">
              <router-link to="/search" class="nav-link">사이트 검색</router-link>
            </li>
          </ul>
          
          <ul class="navbar-nav ms-auto">
            <!-- 로그인 상태: 프로필 드롭다운 -->
            <li v-if="auth.state.isAuthenticated" class="nav-item dropdown">
              <a
                class="nav-link dropdown-toggle d-flex align-items-center"
                href="#"
                role="button"
                data-bs-toggle="dropdown"
                aria-expanded="false"
              >
                <img
                  v-if="auth.state.profilePictureUrl"
                  :src="auth.state.profilePictureUrl"
                  class="navbar-profile-img me-1"
                  referrerpolicy="no-referrer"
                  alt="프로필"
                  @error="onProfileImgError"
                />
                <font-awesome-icon v-else :icon="['fa', 'user-circle']" />
                <span class="ms-1 d-none d-md-inline">{{ auth.state.userName }}</span>
              </a>
              <ul class="dropdown-menu dropdown-menu-end">
                <li>
                  <router-link to="/login" class="dropdown-item">
                    <font-awesome-icon :icon="['fa', 'user-circle']" class="me-2" />
                    프로필
                  </router-link>
                </li>
                <li><hr class="dropdown-divider" /></li>
                <li>
                  <a class="dropdown-item" href="#" @click.prevent="handleLogout">
                    <font-awesome-icon :icon="['fa', 'right-from-bracket']" class="me-2" />
                    로그아웃
                  </a>
                </li>
              </ul>
            </li>
            <!-- 비로그인 상태: 로그인 링크 -->
            <li v-else class="nav-item">
              <router-link to="/login" class="nav-link">
                <font-awesome-icon :icon="['fa', 'user-circle']" class="me-1" />
                <span class="d-none d-md-inline">로그인</span>
              </router-link>
            </li>
          </ul>
        </div>
      </div>
    </nav>

    <router-view />
  </div>
</template>

<style>
html {
  font-size: 14px;
}

.navbar-brand {
  margin-left: 10px;
}

.navbar-text {
  font-weight: bold;
}

.nav-link {
  color: rgba(255, 255, 255, 0.75) !important;
  text-decoration: none !important;
  padding: 0.5rem 1rem !important;
}

.nav-link:hover {
  color: rgba(255, 255, 255, 1) !important;
}

.navbar-nav .nav-link {
  color: rgba(255, 255, 255, 0.75) !important;
}

.navbar-nav .nav-link:hover {
  color: rgba(255, 255, 255, 1) !important;
}

#app {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.navbar-profile-img {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  object-fit: cover;
}

.dropdown-menu {
  font-size: 0.875rem;
}
</style>

<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faUserCircle, faRightFromBracket } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import { authStore } from "./stores/authStore";
import { getApiUrlPath } from "./utils/api";

library.add(faUserCircle, faRightFromBracket);

const auth = authStore;

const handleLogout = async () => {
  try {
    await axios.post(`${getApiUrlPath()}/auth/logout`, {}, { withCredentials: true });
  } catch (error) {
    console.error("Logout error:", error);
  }
  auth.clear();
  localStorage.removeItem("access_token");
  localStorage.removeItem("name");
  localStorage.removeItem("is_authorized");
  localStorage.removeItem("session_expiry");
  window.location.href = "/login";
};

const onProfileImgError = (e) => {
  e.target.style.display = "none";
};
</script>
