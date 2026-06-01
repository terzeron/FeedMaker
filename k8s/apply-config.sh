#!/bin/bash
# Generate/refresh the fm-config ConfigMap from .env (the single source of truth
# for portable app config). Idempotent: safe to re-run on every config change.
#
# Lifecycle note: this is intentionally separate from fm.sh. fm.sh is a one-time
# cluster bootstrap (helm installs, volumes, ingress). This script only syncs
# application config and is run whenever .env changes, followed by a rollout.
#
# Usage:
#   k8s/apply-config.sh            # generate and apply to the cluster
#   k8s/apply-config.sh --dry-run  # print the rendered ConfigMap, apply nothing
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
NAMESPACE="feedmaker"
CONFIGMAP="fm-config"

DRY_RUN=""
[ "${1:-}" = "--dry-run" ] && DRY_RUN="1"

# Portable, NON-secret keys whose RESOLVED value is identical on host and pod.
# Excluded on purpose (kept inline in fm-deployment.yml or in a Secret):
#   - secrets (MYSQL_PASSWORD/ROOT)      -> fm-db-mysql Secret
#   - host-divergent paths/host (PATH, PYTHONPATH, FM_DB_HOST, FM_*_DIR,
#     WEB_SERVICE_ROOT_DIR, WEB_SERVICE_*_DIR_PREFIX -> host filesystem paths)
#   - removed providers (MSG_EMAIL_NHN_CLOUD_*, DEEPL_API_KEY, ANTHROPIC_API_KEY)
CONFIG_KEYS=(
    MYSQL_DATABASE
    MYSQL_USER
    FM_BACKEND_PORT
    FM_FRONTEND_URL
    FM_FACEBOOK_LOGIN_ALLOWED_EMAIL_LIST
    WEB_SERVICE_URL
    WEB_SERVICE_FEED_URL_PREFIX
    WEB_SERVICE_IMAGE_URL_PREFIX
    WEB_SERVICE_PDF_URL_PREFIX
    MSG_CHANNEL
    MSG_EMAIL_SENDER_ADDR
    MSG_EMAIL_SENDER_NAME
    MSG_EMAIL_RECIPIENT_LIST
    MSG_SMTP_SERVER
    MSG_SMTP_PORT
)

if [ ! -f "$ENV_FILE" ]; then
    echo "error: $ENV_FILE not found" >&2
    exit 1
fi

ENV_TMP="$(mktemp)"
trap 'rm -f "$ENV_TMP"' EXIT

# Source .env inside an isolated subshell so ${VAR} interpolation is resolved
# (e.g. WEB_SERVICE_FEED_URL_PREFIX=${WEB_SERVICE_URL}/xml) exactly as the host
# resolves it. The subshell contains the host PATH/PYTHONPATH that .env exports;
# only the shell builtin `printf` runs here, so that pollution is harmless and
# never reaches kubectl. KEY=value lines feed `kubectl --from-env-file`.
(
    set +u
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    for key in "${CONFIG_KEYS[@]}"; do
        printf '%s=%s\n' "$key" "${!key-}"
    done
) > "$ENV_TMP"

# Fail loudly on any key that resolved to empty (missing in .env).
missing="$(awk -F= '$2=="" {print $1}' "$ENV_TMP" | paste -sd' ' -)"
if [ -n "$missing" ]; then
    echo "error: missing/empty keys in $ENV_FILE: $missing" >&2
    exit 1
fi

render() {
    kubectl create configmap "$CONFIGMAP" -n "$NAMESPACE" \
        --from-env-file="$ENV_TMP" --dry-run=client -o yaml
}

if [ -n "$DRY_RUN" ]; then
    render
else
    render | kubectl apply -f -
    echo "Applied ConfigMap '$CONFIGMAP' in namespace '$NAMESPACE'."
    echo "Run 'kubectl rollout restart deployment fm-backend -n $NAMESPACE' (or build.sh) to pick it up."
fi
