/**
 * API 호출을 위한 composable
 */
import { ref } from 'vue';
import axios from 'axios';
import { getApiUrlPath, handleApiError } from '@/utils/api';

/**
 * CSRF 토큰을 가져오는 헬퍼 함수
 * localStorage 우선 조회, 없으면 쿠키에서 조회
 */
function getCsrfToken() {
  // 1. localStorage에서 먼저 조회 (cross-origin 쿠키 접근 제한 우회)
  const localToken = localStorage.getItem('csrf_token');
  if (localToken) {
    return localToken;
  }

  // 2. 쿠키에서 조회 (fallback)
  const value = `; ${document.cookie}`;
  const parts = value.split(`; csrf_token=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

export function useApiCall() {
  const loading = ref(false);
  const error = ref(null);

  /**
   * 표준화된 API 호출 함수
   * @param {string} endpoint - API 엔드포인트
   * @param {Object} options - 요청 옵션
   * @returns {Promise} API 응답
   */
  const apiCall = async (endpoint, options = {}) => {
    loading.value = true;
    error.value = null;

    try {
      // CSRF 토큰을 읽어서 헤더에 추가
      const csrfToken = getCsrfToken();
      const headers = { ...options.headers };
      if (csrfToken) {
        headers['X-CSRF-Token'] = csrfToken;
      }

      const config = {
        method: 'GET',
        ...options,
        headers,
        url: getApiUrlPath() + endpoint,
        withCredentials: true  // httpOnly 쿠키를 포함하여 전송 (CSRF 방지를 위해 SameSite 속성과 함께 사용)
      };

      const response = await axios(config);
      
      // API 응답에서 status가 failure인 경우 처리
      if (response.data && response.data.status === 'failure') {
        throw new Error(response.data.message || 'API call failed');
      }

      return response.data;
    } catch (err) {
      error.value = err.message;
      handleApiError(err, `API call to ${endpoint}`);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  /**
   * GET 요청
   */
  const get = (endpoint, params = {}) => {
    return apiCall(endpoint, { 
      method: 'GET',
      params 
    });
  };

  /**
   * POST 요청
   */
  const post = (endpoint, data = {}) => {
    return apiCall(endpoint, {
      method: 'POST',
      data
    });
  };

  /**
   * PUT 요청
   */
  const put = (endpoint, data = {}) => {
    return apiCall(endpoint, {
      method: 'PUT',
      data
    });
  };

  /**
   * DELETE 요청
   */
  const del = (endpoint) => {
    return apiCall(endpoint, {
      method: 'DELETE'
    });
  };

  return {
    loading,
    error,
    apiCall,
    get,
    post,
    put,
    del
  };
}