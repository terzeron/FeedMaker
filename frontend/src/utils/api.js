// API 관련 공통 함수들
export const getApiUrlPath = () => {
  return process.env.VUE_APP_API_URL || "http://localhost:8010";
};

// API 기본 설정
export const apiConfig = {
  baseURL: getApiUrlPath(),
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
}; 