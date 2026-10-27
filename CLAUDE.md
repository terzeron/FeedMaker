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
./build.sh             # Docker 이미지 빌드 및 레지스트리 푸시 (requires .env)
```

## Environment

- `.env` 파일 필요 (빌드/배포 시): `FM_BACKEND_PORT` 등 설정
- 백엔드 환경 변수는 `bin/feed_maker_util.py`의 `Env` 클래스 참조
- Python 3.12 전용 (`requires-python = ">=3.12,<3.13"`)
