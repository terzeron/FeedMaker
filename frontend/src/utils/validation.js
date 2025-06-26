/**
 * 유효성 검사 관련 유틸리티 함수들
 */

/**
 * 이메일 유효성 검사
 * @param {string} email - 검사할 이메일
 * @returns {boolean} 유효성 여부
 */
export const isValidEmail = (email) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

/**
 * URL 유효성 검사
 * @param {string} url - 검사할 URL
 * @returns {boolean} 유효성 여부
 */
export const isValidUrl = (url) => {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
};

/**
 * 필수 필드 검사
 * @param {*} value - 검사할 값
 * @returns {boolean} 유효성 여부
 */
export const isRequired = (value) => {
  if (value === null || value === undefined) return false;
  if (typeof value === 'string') return value.trim().length > 0;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === 'object') return Object.keys(value).length > 0;
  return Boolean(value);
};

/**
 * 최소 길이 검사
 * @param {string} value - 검사할 값
 * @param {number} minLength - 최소 길이
 * @returns {boolean} 유효성 여부
 */
export const minLength = (value, minLength) => {
  return typeof value === 'string' && value.length >= minLength;
};

/**
 * 최대 길이 검사
 * @param {string} value - 검사할 값
 * @param {number} maxLength - 최대 길이
 * @returns {boolean} 유효성 여부
 */
export const maxLength = (value, maxLength) => {
  return typeof value === 'string' && value.length <= maxLength;
};

/**
 * 숫자 유효성 검사
 * @param {*} value - 검사할 값
 * @returns {boolean} 유효성 여부
 */
export const isNumber = (value) => {
  return !isNaN(value) && !isNaN(parseFloat(value));
};

/**
 * 정수 유효성 검사
 * @param {*} value - 검사할 값
 * @returns {boolean} 유효성 여부
 */
export const isInteger = (value) => {
  return isNumber(value) && Number.isInteger(Number(value));
};

/**
 * 양수 검사
 * @param {*} value - 검사할 값
 * @returns {boolean} 유효성 여부
 */
export const isPositive = (value) => {
  return isNumber(value) && Number(value) > 0;
};

/**
 * 범위 검사
 * @param {*} value - 검사할 값
 * @param {number} min - 최소값
 * @param {number} max - 최대값
 * @returns {boolean} 유효성 여부
 */
export const inRange = (value, min, max) => {
  const num = Number(value);
  return isNumber(value) && num >= min && num <= max;
};

/**
 * JSON 문자열 유효성 검사
 * @param {string} jsonString - 검사할 JSON 문자열
 * @returns {boolean} 유효성 여부
 */
export const isValidJson = (jsonString) => {
  try {
    JSON.parse(jsonString);
    return true;
  } catch {
    return false;
  }
};

/**
 * 파일 확장자 검사
 * @param {string} filename - 파일명
 * @param {string[]} allowedExtensions - 허용된 확장자 배열
 * @returns {boolean} 유효성 여부
 */
export const hasValidExtension = (filename, allowedExtensions) => {
  if (!filename || !Array.isArray(allowedExtensions)) return false;
  const extension = filename.split('.').pop()?.toLowerCase();
  return allowedExtensions.map(ext => ext.toLowerCase()).includes(extension);
};

/**
 * 피드명 유효성 검사 (프로젝트 특화)
 * @param {string} feedName - 피드명
 * @returns {boolean} 유효성 여부
 */
export const isValidFeedName = (feedName) => {
  if (!feedName || typeof feedName !== 'string') return false;
  // 피드명은 영문자, 숫자, 언더스코어, 하이픈만 허용
  const feedNameRegex = /^[a-zA-Z0-9_-]+$/;
  return feedNameRegex.test(feedName) && feedName.length >= 2 && feedName.length <= 50;
};

/**
 * 그룹명 유효성 검사 (프로젝트 특화)
 * @param {string} groupName - 그룹명
 * @returns {boolean} 유효성 여부
 */
export const isValidGroupName = (groupName) => {
  if (!groupName || typeof groupName !== 'string') return false;
  // 그룹명은 영문자, 숫자, 언더스코어만 허용
  const groupNameRegex = /^[a-zA-Z0-9_]+$/;
  return groupNameRegex.test(groupName) && groupName.length >= 2 && groupName.length <= 30;
};