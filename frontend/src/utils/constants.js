/**
 * 애플리케이션 전체에서 사용하는 상수들
 */

// API 관련 상수
export const API_ENDPOINTS = {
  GROUPS: '/groups',
  FEEDS: '/groups/{group}/feeds',
  FEED_DETAIL: '/groups/{group}/feeds/{feed}',
  SEARCH: '/search/{keyword}',
  SEARCH_SITE: '/search_site/{keyword}',
  EXEC_RESULT: '/exec_result',
  PROBLEMS: '/problems/{type}',
  PUBLIC_FEEDS: '/public_feeds/{feed}',
  SITE_CONFIG: '/groups/{group}/site_config'
};

// 피드 상태
export const FEED_STATUS = {
  ACTIVE: 'active',
  INACTIVE: 'inactive',
  ERROR: 'error',
  RUNNING: 'running'
};

// 문제 유형
export const PROBLEM_TYPES = {
  STATUS_INFO: 'status_info',
  PROGRESS_INFO: 'progress_info',
  PUBLIC_FEED_INFO: 'public_feed_info',
  HTML_INFO: 'html_info',
  ELEMENT_INFO: 'element_info',
  LIST_URL_INFO: 'list_url_info'
};

// 버튼 상태
export const BUTTON_STATES = {
  IDLE: 'idle',
  LOADING: 'loading',
  SUCCESS: 'success',
  ERROR: 'error'
};

// 알림 타입
export const NOTIFICATION_TYPES = {
  INFO: 'info',
  SUCCESS: 'success',
  WARNING: 'warning',
  ERROR: 'error'
};

// 파일 크기 단위
export const FILE_SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB'];

// 날짜 포맷
export const DATE_FORMATS = {
  SHORT: 'YYYY-MM-DD',
  LONG: 'YYYY-MM-DD HH:mm:ss',
  DISPLAY: 'YYYY년 MM월 DD일',
  TIME_ONLY: 'HH:mm:ss'
};

// 정규표현식 패턴
export const REGEX_PATTERNS = {
  EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  URL: /^https?:\/\/.+/,
  FEED_NAME: /^[a-zA-Z0-9_-]+$/,
  GROUP_NAME: /^[a-zA-Z0-9_]+$/,
  PHONE: /^[0-9-+().\s]+$/
};

// 기본 설정값
export const DEFAULT_CONFIG = {
  API_TIMEOUT: 30000, // 30초
  DEBOUNCE_DELAY: 300, // 300ms
  PAGINATION_SIZE: 20,
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
  ALLOWED_IMAGE_TYPES: ['jpg', 'jpeg', 'png', 'gif', 'webp'],
  ALLOWED_DOCUMENT_TYPES: ['pdf', 'doc', 'docx', 'txt']
};

// 에러 메시지
export const ERROR_MESSAGES = {
  NETWORK_ERROR: '네트워크 연결을 확인해주세요.',
  UNAUTHORIZED: '로그인이 필요합니다.',
  FORBIDDEN: '접근 권한이 없습니다.',
  NOT_FOUND: '요청한 리소스를 찾을 수 없습니다.',
  SERVER_ERROR: '서버 오류가 발생했습니다.',
  VALIDATION_ERROR: '입력값을 확인해주세요.',
  FILE_TOO_LARGE: '파일 크기가 너무 큽니다.',
  INVALID_FILE_TYPE: '허용되지 않는 파일 형식입니다.'
};

// 성공 메시지
export const SUCCESS_MESSAGES = {
  SAVE_SUCCESS: '저장되었습니다.',
  DELETE_SUCCESS: '삭제되었습니다.',
  UPDATE_SUCCESS: '업데이트되었습니다.',
  UPLOAD_SUCCESS: '업로드되었습니다.',
  SEND_SUCCESS: '전송되었습니다.'
};

// 로컬 스토리지 키
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'auth_token',
  USER_PREFERENCES: 'user_preferences',
  THEME: 'theme',
  LANGUAGE: 'language'
};

// 테마 설정
export const THEMES = {
  LIGHT: 'light',
  DARK: 'dark',
  AUTO: 'auto'
};

// 언어 설정
export const LANGUAGES = {
  KO: 'ko',
  EN: 'en'
};