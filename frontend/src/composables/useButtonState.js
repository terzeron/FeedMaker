/**
 * 버튼 상태 관리를 위한 composable
 */
import { ref } from 'vue';

export function useButtonState() {
  const buttonStates = ref({});

  /**
   * 버튼을 로딩 상태로 설정합니다
   * @param {string} buttonRef - 버튼 참조 키
   * @param {Object} refs - Vue refs 객체
   */
  const startButton = (buttonRef, refs) => {
    if (refs[buttonRef] && refs[buttonRef].value) {
      refs[buttonRef].value.doShowInitialIcon = false;
      refs[buttonRef].value.doShowSpinner = true;
    }
    buttonStates.value[buttonRef] = 'loading';
  };

  /**
   * 버튼을 기본 상태로 복원합니다
   * @param {string} buttonRef - 버튼 참조 키
   * @param {Object} refs - Vue refs 객체
   */
  const endButton = (buttonRef, refs) => {
    if (refs[buttonRef] && refs[buttonRef].value) {
      refs[buttonRef].value.doShowInitialIcon = true;
      refs[buttonRef].value.doShowSpinner = false;
    }
    buttonStates.value[buttonRef] = 'idle';
  };

  /**
   * 버튼의 현재 상태를 확인합니다
   * @param {string} buttonRef - 버튼 참조 키
   * @returns {boolean} 로딩 중인지 여부
   */
  const isButtonLoading = (buttonRef) => {
    return buttonStates.value[buttonRef] === 'loading';
  };

  /**
   * 모든 버튼을 기본 상태로 복원합니다
   * @param {Object} refs - Vue refs 객체
   */
  const resetAllButtons = (refs) => {
    Object.keys(buttonStates.value).forEach(buttonRef => {
      endButton(buttonRef, refs);
    });
  };

  return {
    buttonStates,
    startButton,
    endButton,
    isButtonLoading,
    resetAllButtons
  };
}