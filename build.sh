#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/.env"

TARGET=${1:-all}
SECURITY_GATE_DIR="${SECURITY_GATE_DIR:-$HOME/k8s/security-gates}"
for gate in image_gate.py manifest_image.py post_deploy.py; do
    [ -r "$SECURITY_GATE_DIR/$gate" ] || { echo "보안 gate가 없어 중단: $gate" >&2; exit 1; }
done

rm -rf */{nohup.out*,run.log*,.mypy_cache,__pycache__,.idea,.git}

GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

build_backend() {
    echo "=== Building backend ==="
    docker build -q --pull --build-arg "APT_REFRESH=${APT_REFRESH:-$(date +%Y%m%d)}" -f backend/Dockerfile \
        --build-arg FM_BACKEND_PORT="$FM_BACKEND_PORT" \
        --build-arg USER_ID="${USER_ID:-$(id -u)}" \
        --build-arg USER_NAME="${USER_NAME:-$(whoami)}" \
        -t terzeron/fm_backend . > /dev/null && \
    python3 -I "$SECURITY_GATE_DIR/image_gate.py" --profile fm-backend --image terzeron/fm_backend:latest && \
    docker tag terzeron/fm_backend:latest registry.terzeron.com/terzeron/fm_backend:latest && \
    docker push -q registry.terzeron.com/terzeron/fm_backend:latest >/dev/null && \
    BACKEND_DIGEST="$(python3 -I "$SECURITY_GATE_DIR/manifest_image.py" resolve --image registry.terzeron.com/terzeron/fm_backend:latest)"
}

build_frontend() {
    echo "=== Building frontend ==="
    docker build -q --build-arg "APT_REFRESH=${APT_REFRESH:-$(date +%Y%m%d)}" -f frontend/Dockerfile --build-arg GIT_COMMIT="$GIT_COMMIT" -t terzeron/fm_frontend . > /dev/null && \
    python3 -I "$SECURITY_GATE_DIR/image_gate.py" --profile fm-frontend --image terzeron/fm_frontend:latest && \
    docker tag terzeron/fm_frontend:latest registry.terzeron.com/terzeron/fm_frontend:latest && \
    docker push -q registry.terzeron.com/terzeron/fm_frontend:latest >/dev/null && \
    FRONTEND_DIGEST="$(python3 -I "$SECURITY_GATE_DIR/manifest_image.py" resolve --image registry.terzeron.com/terzeron/fm_frontend:latest)"
}

rollout_backend() {
    echo "=== Rolling out backend ==="
    kubectl rollout restart deployment fm-backend -n feedmaker && \
    kubectl rollout status deployment/fm-backend -n feedmaker --timeout=300s && \
    python3 -I "$SECURITY_GATE_DIR/post_deploy.py" --profile fm-backend --expected-image "$BACKEND_DIGEST" --timeout 60
}

rollout_frontend() {
    echo "=== Rolling out frontend ==="
    kubectl rollout restart deployment fm-frontend -n feedmaker && \
    kubectl rollout status deployment/fm-frontend -n feedmaker --timeout=300s && \
    python3 -I "$SECURITY_GATE_DIR/post_deploy.py" --profile fm-frontend --expected-image "$FRONTEND_DIGEST" --timeout 60
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
esac || exit "$?"

echo ""
echo "Done! If this is a fresh install, run:"
echo '  python -c "from bin.db import DB; DB.create_all_tables()"'
echo '  python -c "from bin.problem_manager import ProblemManager; pm = ProblemManager(); pm.load_all()"'
