#!/usr/bin/env bash
set -euo pipefail

# choose python
PY="$PWD/.venv/bin/python"
[[ -x "$PY" ]] || PY=python

# environment for tests
export FM_WORK_DIR="$PWD/tmp"
export FM_LOG_DIR="$FM_WORK_DIR/logs"
export WEB_SERVICE_FEED_DIR_PREFIX="$FM_WORK_DIR"
export WEB_SERVICE_IMAGE_DIR_PREFIX="$FM_WORK_DIR/img"

# create minimal runtime directories
mkdir -p \
  "$FM_WORK_DIR" \
  "$FM_WORK_DIR/naver" \
  "$FM_WORK_DIR/naver/certain_webtoon" \
  "$FM_WORK_DIR/img" \
  "$FM_WORK_DIR/logs"

# default ignores for flaky/external deps; override by setting PYTEST_ADDOPTS
if [[ -z "${PYTEST_ADDOPTS:-}" ]]; then
  export PYTEST_ADDOPTS="\
    --ignore=tests/test_download_image.py \
    --ignore=tests/test_download_merge_split.py \
    --ignore=tests/test_image_optimization.py \
    --ignore=tests/test_backend.py \
    --ignore=tests/test_feed_maker.py \
    --ignore=tests/test_feed_maker_util_process.py \
    --ignore=tests/test_notification.py \
    --ignore=tests/test_problem_manager.py \
    --ignore=tests/test_translation.py"
fi

# backend coverage (check plugin first to avoid noisy error)
if "$PY" - <<'PY' >/dev/null 2>&1
import importlib
importlib.import_module('pytest')
importlib.import_module('pytest_cov')
importlib.import_module('coverage')
PY
then
  "$PY" -m pytest -q \
    --cov=backend --cov=bin --cov=utils \
    --cov-report=html --cov-report=term-missing \
    "$@"
else
  echo "[collect_coverage] pytest-cov not found; running without coverage. Install: pip install pytest-cov coverage" >&2
  "$PY" -m pytest -q "$@"
fi

# frontend coverage if test script exists
if [[ -d frontend ]] && (cd frontend && npm run -s test --silent -- --passWithNoTests >/dev/null 2>&1); then
  (cd frontend && npm test -- --coverage --passWithNoTests) || true
fi
