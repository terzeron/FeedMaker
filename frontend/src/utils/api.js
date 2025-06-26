/**
 * API 관련 공통 유틸리티 함수들
 */

/**
 * API URL 경로를 반환합니다.
 * @returns {string} API URL
 */
export const getApiUrlPath = () => {
  return process.env.VUE_APP_API_URL || 'http://localhost:8000';
};

/**
 * API 요청 시 공통 헤더를 반환합니다.
 * @returns {Object} 공통 헤더 객체
 */
export const getCommonHeaders = () => {
  return {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*'
  };
};

/**
 * API 에러를 처리하는 공통 함수입니다.
 * @param {Error} error - 에러 객체
 * @param {string} context - 에러 발생 컨텍스트
 */
export const handleApiError = (error, context = '') => {
  console.error(`API Error ${context}:`, error);
  
  if (error.response) {
    // 서버가 응답했지만 상태 코드가 2xx가 아닌 경우
    console.error('Error data:', error.response.data);
    console.error('Error status:', error.response.status);
  } else if (error.request) {
    // 요청이 만들어졌지만 응답을 받지 못한 경우
    console.error('No response received:', error.request);
  } else {
    // 요청을 설정하는 중에 오류가 발생한 경우
    console.error('Error message:', error.message);
  }
};