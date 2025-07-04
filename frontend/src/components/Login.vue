<template>
  <div class="container-fluid">
    <div class="row">
      <div class="col-12">
        <div id="facebookAuthView">
          <div>
            <FacebookAuth @auth-initialized="authInitialized" ref="authRef" />
            <div>
              <div class="alert alert-info">
                <strong>디버깅 정보:</strong><br>
                initialized={{ initialized }}, accessToken={{ accessToken }},
                status={{ status }}, profile={{ profile }}
              </div>
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
import { useStorage } from "@vueuse/core";
import FacebookAuth from "./FacebookAuth.vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faFacebook } from "@fortawesome/free-brands-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

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

// Session storage - Changed to localStorage for longer session persistence
const sessionAccessToken = useStorage("access_token", null, localStorage);
const sessionName = useStorage("name", null, localStorage);
const sessionIsAuthorized = useStorage("is_authorized", false, localStorage);
const sessionExpiry = useStorage("session_expiry", null, localStorage);

const is_logged = computed(() => {
  // Check if session is expired
  if (sessionExpiry.value && new Date().getTime() > sessionExpiry.value) {
    console.log("Session expired, clearing data");
    clearSessionData();
    return false;
  }
  return sessionAccessToken.value !== null;
});

const name = computed(() => {
  return sessionName.value;
});

const authInitialized = () => {
  console.log("Facebook Auth initialized in Login component");
  initialized.value = true;
  console.log("Initialized value set to:", initialized.value);
};

const safeSplit = (str, delimiter) => {
  if (str && str.includes(delimiter)) {
    return str.split(delimiter);
  }
  return [str];
};

const login = async () => {
  console.log("Login button clicked");
  console.log("Initialized:", initialized.value);
  console.log("AuthRef:", authRef.value);
  console.log("AuthRef isInitialized:", authRef.value?.isInitialized?.());
  
  if (sessionIsAuthorized.value) {
    console.log("Already authorized, redirecting to result");
    await router.push("/result");
    return;
  }

  // Facebook SDK 초기화 상태를 더 정확하게 확인
  const isFacebookReady = initialized.value && authRef.value && authRef.value.isInitialized?.();
  
  if (!isFacebookReady) {
    console.error("Facebook Auth is not initialized. Please wait...");
    console.log("Initialized:", initialized.value);
    console.log("AuthRef exists:", !!authRef.value);
    console.log("AuthRef isInitialized:", authRef.value?.isInitialized?.());
    alert("Facebook Auth가 아직 초기화되지 않았습니다. 잠시 후 다시 시도해주세요.");
    return;
  }

  if (!authRef.value) {
    console.error("AuthRef is not available");
    alert("Facebook Auth 참조를 찾을 수 없습니다.");
    return;
  }

  try {
    console.log("Attempting to login...");
    accessToken.value = await authRef.value.login();
    console.log("Login successful, access token:", accessToken.value);
    
    if (accessToken.value) {
      sessionAccessToken.value = accessToken.value;
      console.log("logged in");
    }

    profile.value = await authRef.value.getProfile();
    console.log("Profile retrieved:", profile.value);
    
    if (profile.value && profile.value["name"]) {
      sessionName.value = profile.value["name"];
    }
    
    const loginAllowedEmaillist = safeSplit(
      process.env.VUE_APP_FACEBOOK_LOGIN_ALLOWED_EMAIL_LIST,
      ","
    );
    console.log("Allowed emails:", loginAllowedEmaillist);
    console.log("User email:", profile.value?.["email"]);
    
    if (
      profile.value &&
      loginAllowedEmaillist.includes(profile.value["email"])
    ) {
      sessionIsAuthorized.value = true;
      // Set session expiry - default 30 days, can be configured via environment variable
      const sessionDays = process.env.VUE_APP_SESSION_EXPIRY_DAYS || 30;
      sessionExpiry.value = new Date().getTime() + (sessionDays * 24 * 60 * 60 * 1000);
      console.log(
        "authorized as " +
          profile.value["name"] +
          " (" +
          profile.value["email"] +
          ") - Session expires in " + sessionDays + " days"
      );
    } else {
      console.log("User not authorized:", profile.value?.["email"]);
      alert("허용되지 않은 이메일입니다: " + profile.value?.["email"]);
      return;
    }

    await router.push("/result");
  } catch (error) {
    console.error("Login error:", error);
    alert("로그인 중 오류가 발생했습니다: " + error.message);
  }
};

const logout = async () => {
  console.log("Logout button clicked");
  
  try {
    clearSessionData();

    if (authRef.value) {
      await authRef.value.logout();
    }

    await router.push("/result");
  } catch (error) {
    console.error("Logout error:", error);
    alert("로그아웃 중 오류가 발생했습니다: " + error.message);
  }
};

onMounted(() => {
  console.log("Login component mounted");
  console.log("Environment variables:");
  console.log("VUE_APP_FACEBOOK_APP_ID:", process.env.VUE_APP_FACEBOOK_APP_ID);
  console.log("VUE_APP_FACEBOOK_LOGIN_ALLOWED_EMAIL_LIST:", process.env.VUE_APP_FACEBOOK_LOGIN_ALLOWED_EMAIL_LIST);

  // Migrate existing sessionStorage data to localStorage for backward compatibility
  migrateSessionData();

  console.log("Session data:", {
    accessToken: sessionAccessToken.value,
    name: sessionName.value,
    isAuthorized: sessionIsAuthorized.value,
  });
});

// Migrate sessionStorage data to localStorage for longer session persistence
const migrateSessionData = () => {
  try {
    const sessionAccessTokenOld = sessionStorage.getItem("access_token");
    const sessionNameOld = sessionStorage.getItem("name");
    const sessionIsAuthorizedOld = sessionStorage.getItem("is_authorized");

    if (sessionAccessTokenOld && !sessionAccessToken.value) {
      sessionAccessToken.value = JSON.parse(sessionAccessTokenOld);
      console.log("Migrated access_token from sessionStorage to localStorage");
    }

    if (sessionNameOld && !sessionName.value) {
      sessionName.value = JSON.parse(sessionNameOld);
      console.log("Migrated name from sessionStorage to localStorage");
    }

    if (sessionIsAuthorizedOld && !sessionIsAuthorized.value) {
      sessionIsAuthorized.value = JSON.parse(sessionIsAuthorizedOld);
      // Set expiry for migrated sessions - default 30 days, can be configured via environment variable
      if (sessionIsAuthorized.value && !sessionExpiry.value) {
        const sessionDays = process.env.VUE_APP_SESSION_EXPIRY_DAYS || 30;
        sessionExpiry.value = new Date().getTime() + (sessionDays * 24 * 60 * 60 * 1000);
        console.log("Set expiry for migrated session - " + sessionDays + " days");
      }
      console.log("Migrated is_authorized from sessionStorage to localStorage");
    }

    // Clear old sessionStorage data after migration
    if (sessionAccessTokenOld || sessionNameOld || sessionIsAuthorizedOld) {
      sessionStorage.removeItem("access_token");
      sessionStorage.removeItem("name");
      sessionStorage.removeItem("is_authorized");
      console.log("Cleared old sessionStorage data");
    }
  } catch (error) {
    console.error("Error during session data migration:", error);
  }
};

// Clear session data
const clearSessionData = () => {
  sessionAccessToken.value = null;
  sessionName.value = null;
  sessionIsAuthorized.value = false;
  sessionExpiry.value = null;
};
</script>
