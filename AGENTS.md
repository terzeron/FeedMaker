# AGENTS.md

This file provides guidance to AI coding assistants (Claude, Codex, Gemini, etc.) when working with code in this repository.

## Project Overview

**FeedMaker** is a web application for creating RSS feeds by crawling websites. It automates the process of extracting content from web pages and generating RSS feeds with comprehensive error handling and monitoring capabilities.

### Key Features

- Web crawling with both regular HTTP and headless browser support
- HTML content extraction using CSS selectors
- RSS feed generation and management
- Web-based UI for feed configuration and monitoring
- Database-backed feed metadata and progress tracking
- Git-based version control for generated feeds

## Technology Stack

### Backend

- **Python 3.12** - Core language
- **FastAPI** - REST API framework
- **MySQL/MariaDB** - Primary database
- **Selenium** - Headless browser automation
- **BeautifulSoup/lxml** - HTML parsing

### Frontend

- **Vue 3** - JavaScript framework
- **Bootstrap** - UI styling
- **Axios** - HTTP client

### Infrastructure

- **Docker** - Containerization
- **Git** - Version control for feeds and code
- **pytest** - Testing framework
- **uv** - Python package and environment manager

## Getting Started

### Prerequisites

- Python 3.12 (via uv)
- Node.js and npm (for frontend)
- MySQL/MariaDB database
- Docker (optional, for containerized deployment)

### Initial Setup

1. **Initialize database**:

   ```bash
   python -c "from bin.db import DB; DB.create_all_tables()"
   ```

2. **Install frontend dependencies**:

   ```bash
   cd frontend && npm install
   ```

3. **Load problem manager data**:
   ```bash
   python -c "from bin.problem_manager import ProblemManager; pm = ProblemManager(); pm.load_all()"
   ```

## Development Commands

### Backend Development

```bash
# Run backend server
uvicorn backend.main:app --reload

# Run feed generation
python bin/run.py [options]
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run development server (hot-reload enabled)
npm run serve

# Build for production
npm run build

# Lint and fix files
npm run lint
```

### Testing

```bash
# Run all tests
uv run pytest tests/

# Run specific test module
uv run pytest tests/test_<module_name>.py

# Run with verbose output
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=bin --cov=backend --cov=utils
```

### Code Quality

```bash
# Type checking
uv run mypy --show-error-codes

# Linting
uv run ruff check .
```

### Docker Build & Deploy

```bash
# Build and push containers
./build.sh

# The script builds both frontend and backend Docker images
```

## Architecture

### System Components

```
┌─────────────────┐
│   Frontend UI   │ (Vue.js)
│  (Vue.js/Bootstrap)│
└────────┬────────┘
         │ REST API
         ▼
┌─────────────────┐
│   Backend API   │ (FastAPI)
│    (FastAPI)    │
└────────┬────────┘
         │
         ├──────────► Database (MySQL/MariaDB)
         │
         ▼
┌─────────────────┐
│ Feed Processing │
│     Engine      │
└─────────────────┘
         │
         ├──────────► Web Crawling
         ├──────────► Content Extraction
         └──────────► RSS Generation
```

### Core Components

#### 1. Backend API (`backend/`)

- **`main.py`** - FastAPI application entry point
- **`feed_maker_manager.py`** - Feed management operations
- **Database integration** via `bin/db.py` and `bin/models.py`
- RESTful endpoints for feed CRUD operations

#### 2. Frontend Web UI (`frontend/`)

- **Vue.js 2.x SPA** with component-based architecture
- **Key components**:
  - Feed management and configuration
  - Search and filtering
  - Problem monitoring dashboard
- **Authentication** via Facebook OAuth
- **Styling** with Bootstrap

#### 3. Feed Processing Engine (`bin/`)

- **`run.py`** (FeedMakerRunner) - Main orchestrator for feed generation
- **`crawler.py`** - HTTP requests and content fetching
- **`extractor.py`** - HTML parsing and content extraction
- **`feed_maker.py`** - RSS XML generation
- **`headless_browser_cloak.py`** - cloakbrowser (patched-Chromium) browser automation for JavaScript-heavy and Cloudflare-protected sites
- **Data managers** - Feeds, problems, HTML files, access logs

#### 4. Utilities (`utils/`)

- Image processing and conversion
- Site-specific search utilities
- Manga-specific helpers
- PDF and image manipulation tools

### Data Flow

1. **Configuration Phase**
   - Each feed has a `conf.json` with three sections:
     - `collection`: List page and item page URLs
     - `extraction`: CSS selectors for content extraction
     - `rss`: Feed metadata (title, description, etc.)

2. **Collection Phase**
   - Crawler fetches list pages to discover content URLs
   - Retrieves individual content pages (regular HTTP or headless browser)

3. **Extraction Phase**
   - HTML parser extracts content using CSS selectors
   - Processes images, text, and metadata

4. **Generation Phase**
   - Formats extracted content into RSS XML
   - Stores in `work/` directory with git versioning

5. **Storage & Versioning**
   - Feeds stored in `work/groups/feeds/`
   - Changes tracked via git

## Project Structure

```
fm_dev/
├── backend/              # FastAPI backend
│   ├── main.py          # API entry point
│   └── feed_maker_manager.py
├── frontend/            # Vue.js frontend
│   ├── src/            # Vue components and app code
│   ├── public/         # Static assets
│   └── dist/           # Built production files
├── bin/                # Core feed processing engine
│   ├── run.py         # Main runner
│   ├── crawler.py     # Web crawler
│   ├── extractor.py   # Content extractor
│   ├── feed_maker.py  # RSS generator
│   ├── db.py          # Database connection
│   └── models.py      # Database models
├── utils/             # Utility functions
├── tests/             # Test files
│   └── resources/     # Test data and fixtures
├── work/              # Generated feeds and configurations
│   └── groups/        # Feed groups
│       └── feeds/     # Individual feed directories
├── logs/              # Application logs
├── tmp/               # Temporary processing files
└── build.sh           # Docker build script
```

## Database Schema

The application uses MySQL/MariaDB with the following key tables:

- **Feed metadata** - Feed configurations and settings
- **Progress tracking** - Feed generation status and history
- **HTML file management** - Cached HTML content and analysis
- **Access logs** - Request tracking and monitoring
- **Problem tracking** - Error logs and issue management
- **Element usage statistics** - CSS selector usage analytics

## Configuration Management

### Feed Configuration (`conf.json`)

Each feed has a JSON configuration file with three main sections:

```json
{
  "collection": {
    "list_url": "...",
    "item_capture_script": "..."
  },
  "extraction": {
    "element_list": [
      {
        "name": "title",
        "selector": "h1.title"
      }
    ]
  },
  "rss": {
    "title": "Feed Title",
    "description": "Feed Description"
  }
}
```

### Environment Variables

Configuration uses `FM_*` prefixed environment variables:

- Database connection settings
- API keys and credentials
- File paths and directories

### Site-Specific Configuration

- Stored as `site_config.json` per group
- Contains site-specific extraction rules
- Test configurations in `tests/resources/`

## Development Guidelines

### Code Style

1. **Python**
   - Follow PEP 8 style guide
   - Use type hints where appropriate
   - Run `black` for consistent formatting
   - Sort imports with `isort`

2. **JavaScript/Vue**
   - Follow Vue.js style guide
   - Use ES6+ features
   - Run ESLint for code quality

### Best Practices

1. **Error Handling**
   - Always use try-catch blocks for I/O operations
   - Log errors with appropriate context
   - Implement retry logic for network requests

2. **Testing**
   - Write unit tests for new features
   - Use test fixtures in `tests/resources/`
   - Maintain test coverage above 80%

3. **Database Operations**
   - Use parameterized queries to prevent SQL injection
   - Close connections properly
   - Use transactions for multi-step operations

4. **Security**
   - Validate and sanitize user input
   - Use secure authentication methods
   - Never commit credentials or API keys

   **Trust model (중요):**
   - 모든 변경/삭제 API 엔드포인트는 `require_admin`으로 보호되며, **admin은 완전히 신뢰되는 주체**로 간주한다.
   - 피드 설정(`conf.json` / `site_config.json`)에 기술된 collection/extraction 명령은
     `FeedMakerRunner`가 **서버에서 그대로 실행**한다. 즉 _피드 설정을 등록·수정할 수 있다는 것은
     사실상 서버에서 임의 명령을 실행할 수 있다는 것과 같다._ (`bin` subprocess 호출 경로)
   - 따라서 admin 계정 권한 부여(`_get_admin_email_set`)는 OS 셸 접근 권한 수준으로 엄격히 통제해야 한다.
   - 경로 파라미터(`group_name`/`feed_name`/`html_file_name`)는 `_validate_name`으로 검증한다.
     검증 문자셋은 `/`를 포함하지 않으므로 디렉터리 구분자 주입은 불가능하다(`.`/`..` 단독 세그먼트는 별도 차단 필요).

5. **Performance**
   - Cache frequently accessed data
   - Use headless browser only when necessary
   - Implement rate limiting for crawlers

### Git Workflow

- **Main branch**: `master` (production-ready code)
- **Development branch**: `develop` (active development)
- Create feature branches from `develop`
- Use descriptive commit messages
- Feed content changes are auto-committed in `work/` directory

## Common Tasks

### Adding a New Feed

1. Create feed directory in `work/groups/<group>/<feed>/`
2. Create `conf.json` with collection, extraction, and RSS settings
3. Test extraction with `python bin/run.py --feed <feed_name>`
4. Verify RSS output in feed directory

### Debugging Feed Issues

1. Check logs in `logs/` directory
2. Review problem manager data
3. Test CSS selectors manually
4. Use headless browser if JavaScript is required

### Modifying Frontend UI

1. Navigate to `frontend/src/components/`
2. Edit relevant Vue component
3. Test with `npm run serve`
4. Build for production with `npm run build`

### Database Migrations

1. Update models in `bin/models.py`
2. Create migration script if needed
3. Test on development database first
4. Apply to production database

## Troubleshooting

### Common Issues

1. **Database connection errors**
   - Check MySQL service is running
   - Verify credentials in environment variables
   - Ensure database exists and is accessible

2. **Frontend build failures**
   - Clear `node_modules` and reinstall: `rm -rf node_modules && npm install`
   - Check Node.js version compatibility
   - Review build logs for specific errors

3. **Feed generation failures**
   - Verify website is accessible
   - Check CSS selectors are still valid
   - Review crawler logs for HTTP errors
   - Try using headless browser mode

4. **Selenium/Browser issues**
   - Ensure ChromeDriver is installed and compatible
   - Check browser binary path configuration
   - Verify sufficient system resources

## Additional Resources

- Project repository: Check README.md for latest updates
- API documentation: Available at `/docs` when backend is running
- Test resources: `tests/resources/` contains sample configs and data

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **FeedMaker** (6129 symbols, 12344 relationships, 142 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/FeedMaker/context` | Codebase overview, check index freshness |
| `gitnexus://repo/FeedMaker/clusters` | All functional areas |
| `gitnexus://repo/FeedMaker/processes` | All execution flows |
| `gitnexus://repo/FeedMaker/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
