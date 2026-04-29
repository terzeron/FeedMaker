<!-- gitnexus:start -->

# GitNexus — Code Intelligence

This project is indexed by GitNexus as **FeedMaker** (5416 symbols, 10070 relationships, 114 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource                                   | Use for                                  |
| ------------------------------------------ | ---------------------------------------- |
| `gitnexus://repo/FeedMaker/context`        | Codebase overview, check index freshness |
| `gitnexus://repo/FeedMaker/clusters`       | All functional areas                     |
| `gitnexus://repo/FeedMaker/processes`      | All execution flows                      |
| `gitnexus://repo/FeedMaker/process/{name}` | Step-by-step execution trace             |

## CLI

| Task                                         | Read this skill file                                        |
| -------------------------------------------- | ----------------------------------------------------------- |
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md`       |
| Blast radius / "What breaks if I change X?"  | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?"             | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md`       |
| Rename / extract / split / refactor          | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md`     |
| Tools, resources, schema reference           | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md`           |
| Index, status, clean, wiki CLI commands      | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md`             |

<!-- gitnexus:end -->

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
