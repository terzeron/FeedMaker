/**
 * 날짜 관련 공통 유틸리티 함수들
 */

/**
 * 날짜 문자열에서 날짜 부분만 추출합니다 (YYYY-MM-DD)
 * @param {string} dateStr - ISO 날짜 문자열 또는 날짜 문자열
 * @returns {string} YYYY-MM-DD 형식의 날짜 문자열
 */
export const getShortDate = (dateStr) => {
  if (!dateStr) return '';
  
  // ISO 8601 형식인 경우 T로 분리
  if (dateStr.includes('T')) {
    return dateStr.split('T')[0];
  }
  
  // 이미 YYYY-MM-DD 형식인 경우 그대로 반환
  if (dateStr.match(/^\d{4}-\d{2}-\d{2}$/)) {
    return dateStr;
  }
  
  // Date 객체로 변환 후 포맷팅
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) {
      return '';
    }
    return date.toISOString().split('T')[0];
  } catch (error) {
    console.error('Date parsing error:', error);
    return '';
  }
};

/**
 * 날짜 문자열을 사용자 친화적인 형식으로 포맷팅합니다
 * @param {string} dateStr - 날짜 문자열
 * @param {string} format - 포맷 형식 ('short', 'long', 'time')
 * @returns {string} 포맷팅된 날짜 문자열
 */
export const formatDate = (dateStr, format = 'short') => {
  if (!dateStr) return '';
  
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) {
      return '';
    }
    
    const options = {
      short: { year: 'numeric', month: '2-digit', day: '2-digit' },
      long: { year: 'numeric', month: 'long', day: 'numeric' },
      time: { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }
    };
    
    return date.toLocaleDateString('ko-KR', options[format] || options.short);
  } catch (error) {
    console.error('Date formatting error:', error);
    return '';
  }
};

/**
 * 현재 날짜를 YYYY-MM-DD 형식으로 반환합니다
 * @returns {string} 현재 날짜 문자열
 */
export const getCurrentDate = () => {
  return new Date().toISOString().split('T')[0];
};

/**
 * 두 날짜 사이의 차이를 일 단위로 계산합니다
 * @param {string} startDate - 시작 날짜
 * @param {string} endDate - 종료 날짜 (기본값: 현재 날짜)
 * @returns {number} 일 수 차이
 */
export const getDaysDifference = (startDate, endDate = null) => {
  try {
    const start = new Date(startDate);
    const end = endDate ? new Date(endDate) : new Date();
    
    if (isNaN(start.getTime()) || isNaN(end.getTime())) {
      return 0;
    }
    
    const diffTime = Math.abs(end - start);
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  } catch (error) {
    console.error('Date difference calculation error:', error);
    return 0;
  }
};