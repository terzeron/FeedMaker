/**
 * 알림 관련 composable
 */
import { ref } from 'vue';

export function useNotification() {
  const notification = ref({
    show: false,
    message: '',
    type: 'info', // 'info', 'success', 'warning', 'error'
    duration: 3000
  });

  /**
   * 알림 표시
   * @param {string} message - 알림 메시지
   * @param {string} type - 알림 타입
   * @param {number} duration - 표시 시간 (ms)
   */
  const showNotification = (message, type = 'info', duration = 3000) => {
    notification.value = {
      show: true,
      message,
      type,
      duration
    };

    // 자동으로 닫기
    if (duration > 0) {
      setTimeout(() => {
        hideNotification();
      }, duration);
    }
  };

  /**
   * 알림 숨기기
   */
  const hideNotification = () => {
    notification.value.show = false;
  };

  /**
   * 성공 알림
   */
  const showSuccess = (message, duration = 3000) => {
    showNotification(message, 'success', duration);
  };

  /**
   * 에러 알림
   */
  const showError = (message, duration = 5000) => {
    showNotification(message, 'error', duration);
  };

  /**
   * 경고 알림
   */
  const showWarning = (message, duration = 4000) => {
    showNotification(message, 'warning', duration);
  };

  /**
   * 정보 알림
   */
  const showInfo = (message, duration = 3000) => {
    showNotification(message, 'info', duration);
  };

  /**
   * 확인 다이얼로그
   * @param {string} message - 확인 메시지
   * @returns {boolean} 사용자 선택 결과
   */
  const confirm = (message) => {
    return window.confirm(message);
  };

  /**
   * 단순 경고 다이얼로그
   * @param {string} message - 경고 메시지
   */
  const alert = (message) => {
    window.alert(message);
  };

  return {
    notification,
    showNotification,
    hideNotification,
    showSuccess,
    showError,
    showWarning,
    showInfo,
    confirm,
    alert
  };
}