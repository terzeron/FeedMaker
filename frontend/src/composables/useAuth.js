/**
 * 인증 관련 composable
 */
import { ref, computed, getCurrentInstance } from 'vue';
import { useRouter } from 'vue-router';

export function useAuth() {
  const router = useRouter();
  const instance = getCurrentInstance();
  const session = instance?.appContext.config.globalProperties.$session;

  const isAuthorized = ref(false);

  /**
   * 인증 상태 확인
   */
  const checkAuth = () => {
    if (session) {
      isAuthorized.value = session.get('is_authorized') || false;
      return isAuthorized.value;
    }
    return false;
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
      isAuthorized.value = authorized;
    }
  };

  /**
   * 로그아웃
   */
  const logout = () => {
    setAuth(false);
    redirectToLogin();
  };

  // computed 속성
  const isLoggedIn = computed(() => isAuthorized.value);

  // 초기화
  checkAuth();

  return {
    isAuthorized,
    isLoggedIn,
    checkAuth,
    requireAuth,
    setAuth,
    logout,
    redirectToLogin
  };
}