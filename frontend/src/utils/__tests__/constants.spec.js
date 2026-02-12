import {
  API_ENDPOINTS,
  FEED_STATUS,
  PROBLEM_TYPES,
  BUTTON_STATES,
  NOTIFICATION_TYPES,
  FILE_SIZE_UNITS,
  DATE_FORMATS,
  REGEX_PATTERNS,
  DEFAULT_CONFIG,
  ERROR_MESSAGES,
  SUCCESS_MESSAGES,
  STORAGE_KEYS,
  THEMES,
  LANGUAGES
} from '@/utils/constants';

describe('utils/constants', () => {
  it('API_ENDPOINTS contains required paths', () => {
    expect(API_ENDPOINTS.GROUPS).toBe('/groups');
    expect(API_ENDPOINTS.FEEDS).toContain('{group}');
    expect(API_ENDPOINTS.FEED_DETAIL).toContain('{feed}');
    expect(API_ENDPOINTS.SEARCH).toContain('{keyword}');
    expect(API_ENDPOINTS.EXEC_RESULT).toBe('/exec_result');
    expect(API_ENDPOINTS.PROBLEMS).toContain('{type}');
    expect(API_ENDPOINTS.PUBLIC_FEEDS).toContain('{feed}');
    expect(API_ENDPOINTS.SITE_CONFIG).toContain('{group}');
  });

  it('FEED_STATUS has all states', () => {
    expect(FEED_STATUS).toEqual({
      ACTIVE: 'active',
      INACTIVE: 'inactive',
      ERROR: 'error',
      RUNNING: 'running'
    });
  });

  it('PROBLEM_TYPES has all types', () => {
    expect(PROBLEM_TYPES.STATUS_INFO).toBe('status_info');
    expect(PROBLEM_TYPES.PROGRESS_INFO).toBe('progress_info');
    expect(PROBLEM_TYPES.PUBLIC_FEED_INFO).toBe('public_feed_info');
    expect(PROBLEM_TYPES.HTML_INFO).toBe('html_info');
    expect(PROBLEM_TYPES.ELEMENT_INFO).toBe('element_info');
    expect(PROBLEM_TYPES.LIST_URL_INFO).toBe('list_url_info');
  });

  it('BUTTON_STATES has all states', () => {
    expect(BUTTON_STATES).toEqual({
      IDLE: 'idle',
      LOADING: 'loading',
      SUCCESS: 'success',
      ERROR: 'error'
    });
  });

  it('NOTIFICATION_TYPES has all types', () => {
    expect(NOTIFICATION_TYPES).toEqual({
      INFO: 'info',
      SUCCESS: 'success',
      WARNING: 'warning',
      ERROR: 'error'
    });
  });

  it('FILE_SIZE_UNITS is ordered correctly', () => {
    expect(FILE_SIZE_UNITS).toEqual(['B', 'KB', 'MB', 'GB', 'TB']);
  });

  it('DATE_FORMATS has expected formats', () => {
    expect(DATE_FORMATS.SHORT).toBe('YYYY-MM-DD');
    expect(DATE_FORMATS.LONG).toContain('HH:mm:ss');
  });

  it('REGEX_PATTERNS validate correctly', () => {
    expect(REGEX_PATTERNS.EMAIL.test('user@example.com')).toBe(true);
    expect(REGEX_PATTERNS.EMAIL.test('invalid')).toBe(false);
    expect(REGEX_PATTERNS.URL.test('https://example.com')).toBe(true);
    expect(REGEX_PATTERNS.URL.test('ftp://bad')).toBe(false);
    expect(REGEX_PATTERNS.FEED_NAME.test('my-feed_1')).toBe(true);
    expect(REGEX_PATTERNS.FEED_NAME.test('has spaces')).toBe(false);
    expect(REGEX_PATTERNS.GROUP_NAME.test('group_1')).toBe(true);
    expect(REGEX_PATTERNS.PHONE.test('+82-10-1234-5678')).toBe(true);
  });

  it('DEFAULT_CONFIG has sensible values', () => {
    expect(DEFAULT_CONFIG.API_TIMEOUT).toBe(30000);
    expect(DEFAULT_CONFIG.DEBOUNCE_DELAY).toBe(300);
    expect(DEFAULT_CONFIG.PAGINATION_SIZE).toBe(20);
    expect(DEFAULT_CONFIG.MAX_FILE_SIZE).toBe(10 * 1024 * 1024);
    expect(DEFAULT_CONFIG.ALLOWED_IMAGE_TYPES).toContain('jpg');
    expect(DEFAULT_CONFIG.ALLOWED_DOCUMENT_TYPES).toContain('pdf');
  });

  it('ERROR_MESSAGES has all messages', () => {
    expect(ERROR_MESSAGES.NETWORK_ERROR).toBeTruthy();
    expect(ERROR_MESSAGES.UNAUTHORIZED).toBeTruthy();
    expect(ERROR_MESSAGES.FORBIDDEN).toBeTruthy();
    expect(ERROR_MESSAGES.NOT_FOUND).toBeTruthy();
    expect(ERROR_MESSAGES.SERVER_ERROR).toBeTruthy();
    expect(ERROR_MESSAGES.VALIDATION_ERROR).toBeTruthy();
    expect(ERROR_MESSAGES.FILE_TOO_LARGE).toBeTruthy();
    expect(ERROR_MESSAGES.INVALID_FILE_TYPE).toBeTruthy();
  });

  it('SUCCESS_MESSAGES has all messages', () => {
    expect(SUCCESS_MESSAGES.SAVE_SUCCESS).toBeTruthy();
    expect(SUCCESS_MESSAGES.DELETE_SUCCESS).toBeTruthy();
    expect(SUCCESS_MESSAGES.UPDATE_SUCCESS).toBeTruthy();
    expect(SUCCESS_MESSAGES.UPLOAD_SUCCESS).toBeTruthy();
    expect(SUCCESS_MESSAGES.SEND_SUCCESS).toBeTruthy();
  });

  it('STORAGE_KEYS has all keys', () => {
    expect(STORAGE_KEYS.AUTH_TOKEN).toBe('auth_token');
    expect(STORAGE_KEYS.USER_PREFERENCES).toBe('user_preferences');
    expect(STORAGE_KEYS.THEME).toBe('theme');
    expect(STORAGE_KEYS.LANGUAGE).toBe('language');
  });

  it('THEMES has all themes', () => {
    expect(THEMES).toEqual({ LIGHT: 'light', DARK: 'dark', AUTO: 'auto' });
  });

  it('LANGUAGES has all languages', () => {
    expect(LANGUAGES).toEqual({ KO: 'ko', EN: 'en' });
  });
});
