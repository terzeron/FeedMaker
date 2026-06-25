# syntax=docker/dockerfile:1
# Multi-stage build: build toolchain (build-essential/git/gnupg/unzip) stays in the
# builder stage and is dropped from the runtime image (CIS Docker 4.3 / M-4).
# Runtime keeps only what the app needs at run time: chromium(+driver), gosu, curl
# (HEALTHCHECK), and the *runtime* shared libs for poppler/heif/cairo native wheels.

# ---------------------------------------------------------------------------
# Stage 1: builder — compiles the venv
# ---------------------------------------------------------------------------
FROM python:3.12-slim@sha256:090ba77e2958f6af52a5341f788b50b032dd4ca28377d2893dcf1ecbdfdfe203 AS builder

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    libpoppler-dev libpoppler-cpp-dev libheif-dev libcairo2-dev \
    build-essential git curl unzip gnupg ca-certificates && \
    apt-get upgrade -y

# uv: pinned official image by digest (integrity-verified binary, no `curl | sh`) — SC-1
COPY --from=ghcr.io/astral-sh/uv:0.11.18@sha256:78bc42400d77b0678ba95765305c826652ed5431f399257271dda681d0318f03 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_SYSTEM_PYTHON=1 UV_LINK_MODE=copy UV_PYTHON=python3.12
COPY pyproject.toml uv.lock README.md /app/
RUN --mount=type=cache,target=/tmp/uv-cache \
    HOME=/tmp XDG_CACHE_HOME=/tmp/.cache UV_CACHE_DIR=/tmp/uv-cache \
    uv sync --locked --no-editable

# ---------------------------------------------------------------------------
# Stage 2: runtime — no compilers. git IS required: FeedMakerManager uses GitPython
# (Repo/index.commit) to version feed configs, so the git executable must be present.
# ---------------------------------------------------------------------------
FROM python:3.12-slim@sha256:090ba77e2958f6af52a5341f788b50b032dd4ca28377d2893dcf1ecbdfdfe203

# Runtime-only: chromium engine + gosu + curl(HEALTHCHECK) + shared libs that the
# compiled wheels (poppler/heif/cairo) link against. Package names resolved from the
# -dev packages' runtime deps on debian (python:3.12-slim base).
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    chromium chromium-driver gosu curl ca-certificates git \
    libpoppler-cpp2 libpoppler147 libheif1 \
    libcairo2 libcairo-gobject2 \
    libfontconfig1 libfreetype6 libjpeg62-turbo libpng16-16t64 && \
    apt-get upgrade -y && \
    # crashpad handler wrapper (same trick as single-stage image)
    printf '#!/bin/sh\nexec /usr/lib/chromium/chrome_crashpad_handler.real "$@" --database=/tmp/crashpad 2>/dev/null || true\n' \
        > /usr/lib/chromium/chrome_crashpad_handler.wrapper && \
    mv /usr/lib/chromium/chrome_crashpad_handler /usr/lib/chromium/chrome_crashpad_handler.real && \
    mv /usr/lib/chromium/chrome_crashpad_handler.wrapper /usr/lib/chromium/chrome_crashpad_handler && \
    chmod +x /usr/lib/chromium/chrome_crashpad_handler && \
    rm -rf /var/lib/apt/lists/*

ARG USER_ID=1000
ARG USER_NAME=terzeron
RUN useradd -l -u $USER_ID $USER_NAME && \
    mkdir -p /app /app/backend /app/bin /app/utils /fma /xml \
        /home/$USER_NAME/.cache/pip /home/$USER_NAME/.local /home/$USER_NAME/.local/bin \
        /run/dbus && \
    chown -R $USER_NAME /app /fma /xml /home/$USER_NAME/.cache /home/$USER_NAME/.local

# Bring the prebuilt venv from the builder (no toolchain copied).
COPY --from=builder --chown=$USER_NAME /app/.venv /app/.venv

WORKDIR /app
# 컨테이너는 stdout-only 로깅 설정을 사용 (readOnlyRootFilesystem 호환, 로그는 k8s 가 수집).
# 호스트 CLI 용 logging.conf(파일 핸들러 포함)와 분리.
COPY logging.docker.conf /app/logging.conf
COPY backend /app/backend
COPY bin /app/bin
COPY utils /app/utils

VOLUME /fma
VOLUME /xml

ENV PATH="/app/.venv/bin:/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:/home/$USER_NAME/.local/bin:/app/bin:/app/utils"
ENV PYTHONPATH="/app"
ENV APP_USER=$USER_NAME
ARG FM_BACKEND_DEFAULT_PORT=8010
ENV FM_BACKEND_PORT=$FM_BACKEND_DEFAULT_PORT

EXPOSE $FM_BACKEND_PORT

# entrypoint at / (root-owned), then drop back to the app user
USER root
COPY backend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -s -o /dev/null http://localhost:8010/auth/me || exit 1

USER $USER_NAME
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "backend.main:app", "--workers", "1", "--host", "0.0.0.0", "--port", "8010", "--log-level", "debug", "--access-log", "--log-config", "/app/logging.conf"]
