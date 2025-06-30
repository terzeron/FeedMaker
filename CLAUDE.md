# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Testing
- **Run all tests**: `cd tests && python -m pytest` 
- **Run specific test**: `cd tests && python -m pytest test_<module_name>.py`
- **Run with verbose output**: `cd tests && python -m pytest -v`

### Code Quality
- **Run type checking**: `mypy bin/ backend/ utils/`
- **Run linting**: `pylint bin/ backend/ utils/`
- **Format code**: `black bin/ backend/ utils/ tests/`
- **Sort imports**: `isort bin/ backend/ utils/ tests/`

### Frontend Development
- **Install dependencies**: `cd frontend && npm install`
- **Run development server**: `cd frontend && npm run serve`
- **Build for production**: `cd frontend && npm run build`
- **Lint frontend code**: `cd frontend && npm run lint`

### Backend Development
- **Run backend server**: `python backend/main.py`
- **Initialize database**: `python -c "from bin.db import DB; DB.create_all_tables()"`
- **Load problem manager data**: `python -c "from bin.problem_manager import ProblemManager; pm = ProblemManager(); pm.load_all()"`

### Docker Build & Deploy
- **Build and push containers**: `./build.sh`
- **Apply environment variables**: `. bin/setup.sh` (if available)

## Architecture Overview

FeedMaker is a web application for creating RSS feeds by crawling websites. The system consists of three main components:

### Core Components

1. **Backend API** (`backend/`)
   - FastAPI-based REST API server (`main.py`)
   - Feed management through `FeedMakerManager` (`feed_maker_manager.py`)
   - Database models and connections (`bin/db.py`, `bin/models.py`)

2. **Frontend Web UI** (`frontend/`)
   - Vue.js 2.x application with Bootstrap styling
   - Components for feed management, search, and problem monitoring
   - Authentication support via Facebook OAuth

3. **Feed Processing Engine** (`bin/`)
   - **Core runner**: `run.py` (FeedMakerRunner) - main orchestrator for feed generation
   - **Web crawling**: `crawler.py` - handles HTTP requests and content fetching
   - **Content extraction**: `extractor.py` - parses HTML and extracts feed items
   - **Feed generation**: `feed_maker.py` - creates RSS XML output
   - **Browser automation**: `headless_browser.py` - uses Selenium for dynamic content
   - **Data management**: Various managers for feeds, problems, HTML files, access logs

4. **Utilities** (`utils/`)
   - Image processing and conversion tools
   - Site search and manga-specific utilities
   - PDF/image manipulation helpers

### Key Data Flow

1. **Configuration**: Each feed has a `conf.json` with collection, extraction, and RSS settings
2. **Collection**: Crawlers fetch list pages and individual content pages
3. **Extraction**: HTML is parsed using CSS selectors to extract content
4. **Feed Generation**: Extracted content is formatted into RSS XML
5. **Storage**: Feeds are stored in `work/` directory with git version control

### Directory Structure

- `work/groups/feeds/` - Feed configurations and generated RSS files
- `frontend/dist/` - Built frontend assets
- `logs/` - Application logs
- `tests/` - Test files with resources and test data
- `tmp/` - Temporary processing files

### Database Schema

Uses MySQL/MariaDB with tables for:
- Feed metadata and configuration
- Progress tracking and status information  
- HTML file management and analysis
- Access logs and problem tracking
- Element usage statistics

### Configuration Management

- Feed configs use JSON format with `collection`, `extraction`, and `rss` sections
- Environment variables configured via `FM_*` prefixed variables
- Site-specific configs stored as `site_config.json` per group
- Test configurations available in `tests/resources/`

The system supports both regular crawling and headless browser automation for JavaScript-heavy sites, with comprehensive error handling and monitoring capabilities.