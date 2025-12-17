/**
 * 인증 관련 composable (httpOnly 쿠키 기반)
 *
 * 보안 개선: localStorage 대신 서버 기반 세션 관리
 * - 인증 상태는 서버에서만 관리
 * - httpOnly 쿠키로 세션 ID 전송
 * - XSS 공격으로부터 안전
 */
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';
import { getApiUrlPath } from '@/utils/api';

export function useAuth() {
  const router = useRouter();
  const isAuthorized = ref(false);
  const userName = ref(null);

  /**
   * 서버에서 인증 상태 확인
   */
  const checkAuth = async () => {
    try {
      const response = await axios.get(
        `${getApiUrlPath()}/auth/me`,
        { withCredentials: true }
      );

      if (response.data.is_authenticated) {
        isAuthorized.value = true;
        userName.value = response.data.name || null;
        return true;
      } else {
        isAuthorized.value = false;
        userName.value = null;
        return false;
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      isAuthorized.value = false;
      userName.value = null;
      return false;
    }
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
  const requireAuth = async () => {
    const authenticated = await checkAuth();
    if (!authenticated) {
      redirectToLogin();
      return false;
    }
    return true;
  };

  /**
   * 로그아웃
   */
  const logout = async () => {
    try {
      await axios.post(
        `${getApiUrlPath()}/auth/logout`,
        {},
        { withCredentials: true }
      );
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      // 로컬 상태 초기화
      isAuthorized.value = false;
      userName.value = null;

      // 기존 localStorage 데이터 정리 (마이그레이션용)
      localStorage.removeItem("access_token");
      localStorage.removeItem("name");
      localStorage.removeItem("is_authorized");
      localStorage.removeItem("session_expiry");

      redirectToLogin();
    }
  };

  /**
   * 세션 데이터 초기화 (deprecated - 하위 호환성용)
   */
  const clearSessionData = () => {
    console.warn('clearSessionData is deprecated. Use logout() instead.');
    isAuthorized.value = false;
    userName.value = null;

    localStorage.removeItem("access_token");
    localStorage.removeItem("name");
    localStorage.removeItem("is_authorized");
    localStorage.removeItem("session_expiry");
  };

  /**
   * 세션 만료 확인 (deprecated - 서버에서 검증)
   */
  const checkSessionExpiry = () => {
    console.warn('checkSessionExpiry is deprecated. Server validates session expiry.');
    return true;
  };

  /**
   * 로그인 설정 (deprecated - 서버에서 관리)
   */
  const setAuth = () => {
    console.warn('setAuth is deprecated. Server manages authentication state.');
  };

  // computed 속성
  const isLoggedIn = computed(() => isAuthorized.value);

  return {
    isAuthorized,
    isLoggedIn,
    userName,
    checkAuth,
    requireAuth,
    logout,
    redirectToLogin,
    // Deprecated functions (하위 호환성)
    setAuth,
    checkSessionExpiry,
    clearSessionData
  };
}
