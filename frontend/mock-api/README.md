# Mock API Server

프론트엔드 개발 및 테스트를 위한 Mock API 서버입니다. OpenAPI 스펙에 기반하여 실제 백엔드 API와 동일한 인터페이스를 제공합니다.

## 설치

```bash
npm install
```

## 사용법

### 1. Mock API만 실행
```bash
npm run mock:api
```

### 2. Mock API와 프론트엔드 동시 실행
```bash
npm run dev:mock
```

## 환경 설정

프론트엔드에서 Mock API를 사용하려면 `.env.development` 파일을 생성하고 다음 내용을 추가하세요:

```
VUE_APP_API_URL=http://localhost:3000
VUE_APP_FACEBOOK_APP_ID=your_facebook_app_id
VUE_APP_FACEBOOK_ADMIN_EMAIL=admin@example.com
```

## Mock 데이터

`db.json` 파일에 Mock 데이터가 정의되어 있습니다. 필요에 따라 이 파일을 수정하여 다른 응답을 테스트할 수 있습니다.

## OpenAPI 스펙 분석 및 업데이트

백엔드 API가 변경되면 Mock API도 업데이트해야 합니다:

```bash
# OpenAPI 스펙 분석 및 누락된 엔드포인트 확인
python analyze_openapi.py
```

이 스크립트는:
- 프로젝트 루트의 `openapi.json`을 분석
- 현재 Mock API 서버와 비교
- 누락된 엔드포인트를 찾아서 코드 생성
- `missing_endpoints_fixed.js` 파일로 출력

## 지원하는 API 엔드포인트

### 기본 엔드포인트
- `GET /exec_result` - 실행 결과 조회
- `GET /groups` - 그룹 목록 조회

### 그룹 관련
- `GET /groups/{group_name}/feeds` - 그룹별 피드 목록 조회
- `PUT /groups/{group_name}/toggle` - 그룹 토글
- `DELETE /groups/{group_name}` - 그룹 삭제

### 피드 관련
- `GET /groups/{group_name}/feeds/{feed_name}` - 피드 정보 조회
- `POST /groups/{group_name}/feeds/{feed_name}` - 피드 생성
- `DELETE /groups/{group_name}/feeds/{feed_name}` - 피드 삭제
- `POST /groups/{group_name}/feeds/{feed_name}/run` - 피드 실행
- `PUT /groups/{group_name}/feeds/{feed_name}/toggle` - 피드 토글
- `GET /groups/{group_name}/feeds/{feed_name}/check_running` - 실행 상태 확인
- `DELETE /groups/{group_name}/feeds/{feed_name}/list` - 리스트 삭제
- `DELETE /groups/{group_name}/feeds/{feed_name}/htmls` - HTML 파일 삭제
- `DELETE /groups/{group_name}/feeds/{feed_name}/htmls/{html_file_name}` - 특정 HTML 파일 삭제

### 설정 관련
- `GET /groups/{group_name}/site_config` - 사이트 설정 조회
- `PUT /groups/{group_name}/site_config` - 사이트 설정 저장

### 검색 관련
- `GET /search/{keyword}` - 피드 검색
- `GET /search_site/{keyword}` - 사이트 검색

### 기타
- `DELETE /public_feeds/{feed_name}` - 공개 피드 삭제
- `GET /problems/{data_type}` - 문제 정보 조회

## 포트

Mock API 서버는 기본적으로 `http://localhost:3000`에서 실행됩니다.

## 환경변수

- `VUE_APP_API_PORT`: Mock API 서버 포트 (기본값: 3000)
- `VUE_APP_API_URL`: 프론트엔드에서 사용할 API URL

## 로그

Mock API 서버는 모든 요청을 콘솔에 로그로 출력합니다:
```
[Mock API] GET /groups
[Mock API] POST /groups/webtoon/feeds/naver_webtoon/run
```

## 파일 구조

```
mock-api/
├── server.js          # Mock API 서버 (메인)
├── db.json            # Mock 데이터
├── analyze_openapi.py # OpenAPI 스펙 분석 및 업데이트 도구
└── README.md          # 이 파일
``` 