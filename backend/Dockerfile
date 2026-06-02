# syntax=docker/dockerfile:1
FROM python:3.12-slim

# root
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    libpoppler-dev libpoppler-cpp-dev libheif-dev libcairo2-dev \
    build-essential git curl unzip gnupg ca-certificates chromium chromium-driver gosu && \
    # base 패키지 보안 패치. chromium은 버전 핀 없이 debian 최신을 추적한다
    # (시스템 chrome + 수동 chromedriver 정렬은 재빌드 타이밍으로 관리).
    apt-get upgrade -y && \
    printf '#!/bin/sh\nexec /usr/lib/chromium/chrome_crashpad_handler.real "$@" --database=/tmp/crashpad 2>/dev/null || true\n' \
        > /usr/lib/chromium/chrome_crashpad_handler.wrapper && \
    mv /usr/lib/chromium/chrome_crashpad_handler /usr/lib/chromium/chrome_crashpad_handler.real && \
    mv /usr/lib/chromium/chrome_crashpad_handler.wrapper /usr/lib/chromium/chrome_crashpad_handler && \
    chmod +x /usr/lib/chromium/chrome_crashpad_handler

ARG USER_ID=1000
ARG USER_NAME=terzeron
RUN useradd -u $USER_ID $USER_NAME && \
    mkdir -p /app /app/backend /app/bin /app/utils /fma /xml /home/$USER_NAME/.cache/pip /home/$USER_NAME/.local /home/$USER_NAME/.local/bin /run/dbus /tmp/logs /app/logs && \
    chown -R $USER_NAME /app /fma /xml /home/$USER_NAME/.cache /home/$USER_NAME/.local /tmp/logs /app/logs

RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    cp /root/.local/bin/uv /usr/local/bin/

# CartoonSplit을 COPY 전에 배치하여 코드 변경 시 캐시 유지
RUN git clone https://github.com/terzeron/CartoonSplit /app/CartoonSplit && \
    rm -rf /app/CartoonSplit/.git /app/CartoonSplit/test && \
    chown -R $USER_NAME /app/CartoonSplit

# user(1000) - 빌드 단계는 앱 유저로 실행
USER $USER_NAME
WORKDIR /app

ENV UV_SYSTEM_PYTHON=1 UV_LINK_MODE=copy UV_PYTHON=python3.12
COPY pyproject.toml uv.lock README.md /app/
RUN --mount=type=cache,target=/tmp/uv-cache,uid=1000 \
    HOME=/tmp XDG_CACHE_HOME=/tmp/.cache UV_CACHE_DIR=/tmp/uv-cache \
    uv sync --locked --no-editable

COPY logging.conf /app
COPY backend /app/backend
COPY bin /app/bin
COPY utils /app/utils

VOLUME /fma
VOLUME /xml
VOLUME /logs

ENV CARTOON_SPLIT_HOME_DIR="/app/CartoonSplit"
ENV PATH="/app/.venv/bin:/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:/home/$USER_NAME/.local/bin:/app/bin:/app/utils"
ENV PYTHONPATH="/app"
ENV APP_USER=$USER_NAME
ARG FM_BACKEND_DEFAULT_PORT=8010
ENV FM_BACKEND_PORT=$FM_BACKEND_DEFAULT_PORT

EXPOSE $FM_BACKEND_PORT

# root로 전환하여 / 에 entrypoint 배치
USER root
COPY backend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 서버 응답 여부로 health 판정 (인증 라우트라 401도 "살아있음"으로 간주, -f 미사용)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -s -o /dev/null http://localhost:8010/auth/me || exit 1

# 이미지 최종 USER는 비root (k8s securityContext runAsUser:1000 과 일치)
USER $USER_NAME
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "backend.main:app", "--workers", "1", "--host", "0.0.0.0", "--port", "8010", "--log-level", "debug", "--access-log", "--log-config", "/app/logging.conf"]
