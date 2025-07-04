/**
 * 인증 관련 composable
 */
import { ref, computed, getCurrentInstance } from 'vue';
import { useRouter } from 'vue-router';
import { useStorage } from '@vueuse/core';

export function useAuth() {
  const router = useRouter();
  const instance = getCurrentInstance();
  const session = instance?.appContext.config.globalProperties.$session;

  const isAuthorized = ref(false);
  
  // Use localStorage for longer session persistence
  const sessionIsAuthorized = useStorage("is_authorized", false, localStorage);
  const sessionExpiry = useStorage("session_expiry", null, localStorage);

  /**
   * 세션 만료 확인
   */
  const checkSessionExpiry = () => {
    if (sessionExpiry.value && new Date().getTime() > sessionExpiry.value) {
      console.log("Session expired, clearing data");
      clearSessionData();
      return false;
    }
    return true;
  };

  /**
   * 세션 데이터 초기화
   */
  const clearSessionData = () => {
    sessionIsAuthorized.value = false;
    sessionExpiry.value = null;
    isAuthorized.value = false;
    
    // Clear other session data
    localStorage.removeItem("access_token");
    localStorage.removeItem("name");
  };

  /**
   * 인증 상태 확인
   */
  const checkAuth = () => {
    // Check session expiry first
    if (!checkSessionExpiry()) {
      return false;
    }
    
    if (session) {
      isAuthorized.value = session.get('is_authorized') || false;
      return isAuthorized.value;
    }
    
    // Fallback to localStorage
    isAuthorized.value = sessionIsAuthorized.value;
    return isAuthorized.value;
  };

  /**
   * 로그인 페이지로 리다이렉트
   */
  const redirectToLogin = () => {
    router.push('/login');
  };

  /**
   * 인증 필요한 페이지 가드
   */
  const requireAuth = () => {
    if (!checkAuth()) {
      redirectToLogin();
      return false;
    }
    return true;
  };

  /**
   * 로그인 설정
   */
  const setAuth = (authorized = true) => {
    if (session) {
      session.set('is_authorized', authorized);
    }
    sessionIsAuthorized.value = authorized;
    isAuthorized.value = authorized;
    
    if (authorized) {
      // Set session expiry - default 30 days, can be configured via environment variable
      const sessionDays = process.env.VUE_APP_SESSION_EXPIRY_DAYS || 30;
      sessionExpiry.value = new Date().getTime() + (sessionDays * 24 * 60 * 60 * 1000);
    } else {
      sessionExpiry.value = null;
    }
  };

  /**
   * 로그아웃
   */
  const logout = () => {
    clearSessionData();
    redirectToLogin();
  };

  // computed 속성
  const isLoggedIn = computed(() => {
    checkSessionExpiry();
    return isAuthorized.value;
  });

  // 초기화
  checkAuth();

  return {
    isAuthorized,
    isLoggedIn,
    checkAuth,
    requireAuth,
    setAuth,
    logout,
    redirectToLogin,
    checkSessionExpiry,
    clearSessionData
  };
}