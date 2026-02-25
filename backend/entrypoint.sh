#!/bin/bash
set -e

# 마운트된 볼륨의 권한을 앱 유저에게 부여 (root로 실행 시에만)
if [ "$(id -u)" = "0" ]; then
    chown -R "$APP_USER:$APP_USER" /fma /xml /app/logs 2>/dev/null || true
    exec gosu "$APP_USER" "$@"
fi

exec "$@"
