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
- **Python 3.x** - Core language
- **FastAPI** - REST API framework
- **MySQL/MariaDB** - Primary database
- **Selenium** - Headless browser automation
- **BeautifulSoup/lxml** - HTML parsing

### Frontend
- **Vue.js 2.x** - JavaScript framework
- **Bootstrap** - UI styling
- **Axios** - HTTP client

### Infrastructure
- **Docker** - Containerization
- **Git** - Version control for feeds and code
- **pytest** - Testing framework

## Getting Started

### Prerequisites
- Python 3.x with pip
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

3. **Configure environment variables** (if available):
   ```bash
   . bin/setup.sh
   ```

4. **Load problem manager data**:
   ```bash
   python -c "from bin.problem_manager import ProblemManager; pm = ProblemManager(); pm.load_all()"
   ```

## Development Commands

### Backend Development

```bash
# Run backend server
python backend/main.py

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
cd tests

# Run all tests
python -m pytest

# Run specific test module
python -m pytest test_<module_name>.py

# Run with verbose output
python -m pytest -v

# Run with coverage
python -m pytest --cov=bin --cov=backend --cov=utils
```

### Code Quality

```bash
# Type checking
mypy bin/ backend/ utils/

# Linting
pylint bin/ backend/ utils/

# Code formatting
black bin/ backend/ utils/ tests/

# Import sorting
isort bin/ backend/ utils/ tests/
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
- **`headless_browser.py`** - Selenium-based browser automation for JavaScript-heavy sites
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
