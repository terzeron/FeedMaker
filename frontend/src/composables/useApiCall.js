/**
 * API 호출을 위한 composable
 */
import { ref } from 'vue';
import axios from 'axios';
import { getApiUrlPath, handleApiError } from '@/utils/api';

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
      const config = {
        method: 'GET',
        ...options,
        url: getApiUrlPath() + endpoint
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