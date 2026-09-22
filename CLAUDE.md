<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **FeedMaker** (6074 symbols, 14233 relationships, 359 execution flows).

> Index stale? Run `node .gitnexus/run.cjs analyze --index-only` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? Bootstrap with `npx`, `bunx`, or `pnpm dlx` — e.g. `bunx gitnexus@latest analyze` (npm 11 npx crash; #1939).

## Always Do

- **MUST run impact before editing.** Use `impact({target: "symbolName", direction: "upstream"})` or `node .gitnexus/run.cjs impact "symbolName" --direction upstream --repo .`; report callers, processes, and risk. Never substitute grep for graph analysis.
- **MUST analyze graph changes before committing.** Use `detect_changes({scope: "all"})` (MCP) or `node .gitnexus/run.cjs detect-changes --scope all --repo .` (CLI fallback). `partial: true` or `truncated: true` is not a clean check — a zero means unseen, not unaffected; re-run it. For regression review: `detect_changes({scope: "compare", base_ref: "master"})` or `node .gitnexus/run.cjs detect-changes --scope compare --base-ref "master" --repo .`.
- MUST warn on HIGH/CRITICAL `risk` pre-edit; never use `riskSharedAxes` to waive a HIGH/CRITICAL `risk` warning. Compare File/symbol: MCP File omits axes; Graph-RAG expands File.
- **MUST treat `risk: UNKNOWN` as unresolved, not as low.** An empty caller set is not evidence the symbol is unused — it can also mean the callers are not resolvable by the index (plain-object property access, dynamic dispatch, cross-language calls). `impact` pairs `UNKNOWN` with a `riskNote` saying so. Confirm with a text search before treating the symbol as safe to change or delete; do not proceed on the strength of a zero.
- **MUST use `query({search_query: "concept"})` for concepts/flows, `context({name: "symbolName"})` for a named symbol, or `impact` for blast radius, on read-only callers, dependencies, imports, or execution flow.** Graph first; text search only for empty/`UNKNOWN`/literals.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method before MCP/CLI impact analysis.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis, and never read `UNKNOWN` as an all-clear — it means the walk could not answer, which is the one verdict that requires confirming by other means.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit before MCP/CLI graph change analysis.

## Resources

| Resource | Use for |
| --- | --- |
| `gitnexus://repo/FeedMaker/context` | Codebase overview, check index freshness |
| `gitnexus://repo/FeedMaker/clusters` | All functional areas |
| `gitnexus://repo/FeedMaker/processes` | All execution flows |
| `gitnexus://repo/FeedMaker/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
| --- | --- |
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus-cli/SKILL.md` |

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
