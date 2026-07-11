#!/bin/bash
set -e

# camoufox 바이너리는 이미지의 /opt/camoufox에 baked돼 있다. 런타임 rootfs는 read-only이고
# camoufox가 기대하는 캐시 경로($HOME/.cache/camoufox; $HOME=/tmp emptyDir)는 재시작마다 비어
# 있으므로, baked 디렉토리로 symlink해 런타임 재다운로드를 막는다. (없으면 camoufox가 첫
# 크롤 때 ~200MB를 다시 받으려 시도한다.)
camoufox_cache="${HOME:-/tmp}/.cache/camoufox"
if [ -d /opt/camoufox ] && [ ! -e "$camoufox_cache" ]; then
    mkdir -p "$(dirname "$camoufox_cache")"
    ln -s /opt/camoufox "$camoufox_cache"
fi

# 마운트된 볼륨의 권한을 앱 유저에게 부여 (root로 실행 시에만)
if [ "$(id -u)" = "0" ]; then
    chown -R "$APP_USER:$APP_USER" /fma /xml 2>/dev/null || true
    exec gosu "$APP_USER" "$@"
fi

exec "$@"
