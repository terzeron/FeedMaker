# CodeGraph — Code Intelligence

이 프로젝트의 그래프 탐색은 CodeGraph로 한다. 인덱스는 `.codegraph/`에 있고,
MCP 서버(`codegraph serve --mcp`)가 파일 변경을 감지해 자동 동기화한다.
`.codegraph/`가 없으면 프로젝트 루트에서 `codegraph init`을 한 번 실행한다.

## Always Do

- 함수·메서드를 고치기 전에 호출자와 영향 범위를 확인한다.
  MCP `codegraph_explore`/caller/impact 도구, 또는 CLI
  `codegraph callers <심볼>`, `codegraph impact <심볼> -d <깊이>`를 쓴다.
- 정방향 추적은 `codegraph callees <심볼>`로 한다.
- 커밋 전 변경 범위는 `git status`와 `git diff --stat`으로 확인한다.
- 결과가 0건이거나 경로가 끊기면 텍스트 검색으로 확인한다.
  클로저·동적 디스패치·콜백을 거치는 호출은 놓칠 수 있다.

## Never Do

- 0건 결과를 "사용처 없음"의 증거로 삼지 않는다.
- GitNexus 도구를 쓰지 않는다. GitNexus는 설치와 인덱스를 모두 제거했다.

# FeedMaker — Project Context

## Architecture

| Directory   | Role                                   |
| ----------- | -------------------------------------- |
| `bin/`      | 크롤링/피드 생성 CLI 엔진 (Python)     |
| `backend/`  | FastAPI REST API 서버                  |
| `frontend/` | Vue 3 웹 어드민 (vue-cli)              |
| `utils/`    | PDF 변환, 이미지 처리 등 독립 유틸리티 |
| `tests/`    | pytest 통합 테스트                     |
| `k8s/`      | Kubernetes 배포 매니페스트             |

## Commands

### Backend

```bash
# 개발 서버
uvicorn backend.main:app --reload

# 테스트
uv run pytest tests/

# 타입 체크 + lint (critical only)
uv run mypy --show-error-codes
uv run ruff check .
```

### Frontend

```bash
cd frontend
npm run serve          # 개발 서버
npm test               # Jest 단위 테스트
npm run test:e2e       # Playwright E2E 테스트
npm run lint           # ESLint
npm run build          # 프로덕션 빌드 (버전 포함)
```

### Build & Deploy

```bash
./build.sh             # 개발 버전 배포: Docker 이미지 빌드 및 레지스트리 푸시 (requires .env)
deploy_and_build       # 리얼 버전 배포 (~/bin/deploy_and_build)
```

- 개발 버전 배포는 `./build.sh`로 실행한다.
- 리얼 버전 배포는 `deploy_and_build`로 실행한다.

## 참고 문서

- Cloudflare challenge 체크박스 자동 클릭: `docs/CLOUDFLARE-CHALLENGE.md` (엔진·사이트 변경 전 먼저 확인)

## Environment

- `.env` 파일 필요 (빌드/배포 시): `FM_BACKEND_PORT` 등 설정
- 백엔드 환경 변수는 `bin/feed_maker_util.py`의 `Env` 클래스 참조
- Python 3.12 전용 (`requires-python = ">=3.12,<3.13"`)

## Authentication

- `FM_FACEBOOK_LOGIN_ALLOWED_EMAIL_LIST`는 로그인과 기존 세션 모두의 접근 경계다.
- `backend/auth.py:get_session`은 매 조회마다 현재 허용 목록을 확인한다. 비어 있거나 설정이 없으면 거절한다.
- 제외된 계정이 요청하면 해당 DB 세션을 만료 연장 전에 삭제한다. 다른 장치의 세션도 각 장치가 요청할 때 삭제한다.
- 계정을 다시 허용해도 이미 삭제한 세션은 복구되지 않는다. 새 로그인이 필요하다.
- 허용 목록은 환경 변수다. 배포 설정 변경 후 Pod를 교체해야 실행 중인 프로세스에 반영된다.
- 폐기한 세션은 보호 API에서 401이다. `/auth/me`는 기존 계약대로 200과 `is_authenticated: false`를 반환한다.
- 회귀 검증: `tests/test_session_revocation.py`. 운영 DB를 사용하지 않고 실제 SQLAlchemy transaction과 HTTP 인증 경로를 검사한다.
