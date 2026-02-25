#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/.env"

TARGET=${1:-all}

rm -rf */{nohup.out*,run.log*,.mypy_cache,__pycache__,.idea,.git}

GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

build_backend() {
    echo "=== Building backend ==="
    docker build -f backend/Dockerfile --build-arg FM_BACKEND_PORT="$FM_BACKEND_PORT" -t terzeron/fm_backend . && \
    docker tag terzeron/fm_backend:latest registry.terzeron.com/terzeron/fm_backend:latest && \
    docker push registry.terzeron.com/terzeron/fm_backend:latest
}

build_frontend() {
    echo "=== Building frontend ==="
    docker build -f frontend/Dockerfile --build-arg GIT_COMMIT="$GIT_COMMIT" -t terzeron/fm_frontend . && \
    docker tag terzeron/fm_frontend:latest registry.terzeron.com/terzeron/fm_frontend:latest && \
    docker push registry.terzeron.com/terzeron/fm_frontend:latest
}

rollout_backend() {
    echo "=== Rolling out backend ==="
    kubectl rollout restart deployment fm-backend -n feedmaker
}

rollout_frontend() {
    echo "=== Rolling out frontend ==="
    kubectl rollout restart deployment fm-frontend -n feedmaker
}

case "$TARGET" in
    backend)
        build_backend && rollout_backend
        ;;
    frontend)
        build_frontend && rollout_frontend
        ;;
    all|"")
        build_backend && build_frontend && rollout_backend && rollout_frontend
        ;;
    *)
        echo "Usage: $0 [backend|frontend]"
        echo "  backend  - Build and rollout backend only"
        echo "  frontend - Build and rollout frontend only"
        echo "  (no arg) - Build and rollout both"
        exit 1
        ;;
esac

echo ""
echo "Done! If this is a fresh install, run:"
echo '  python -c "from bin.db import DB; DB.create_all_tables()"'
echo '  python -c "from bin.problem_manager import ProblemManager; pm = ProblemManager(); pm.load_all()"'
