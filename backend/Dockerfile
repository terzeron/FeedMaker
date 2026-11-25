# syntax=docker/dockerfile:1
# Multi-stage build: build toolchain (build-essential/git/gnupg/unzip) stays in the
# builder stage and is dropped from the runtime image (CIS Docker 4.3 / M-4).
# Runtime keeps only what the app needs at run time: chromium(+driver), gosu, curl
# (HEALTHCHECK), and the *runtime* shared libs for poppler/heif/cairo native wheels.

# uv.lock 전체가 바뀌어도 같은 Camoufox 버전이면 다운로드 캐시를 재사용한다.
# 별도 stage의 출력 파일 내용만 다음 stage의 캐시 키에 포함한다.
FROM python:3.12-slim@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9 AS camoufox-version
COPY uv.lock /tmp/uv.lock
RUN python - <<'PY'
import tomllib
from pathlib import Path

lock = tomllib.loads(Path("/tmp/uv.lock").read_text())
version = next(package["version"] for package in lock["package"] if package["name"] == "camoufox")
Path("/camoufox-requirements.txt").write_text(f"camoufox[geoip]=={version}\n")
PY

# 앱 venv와 apt 주간 갱신에서 독립된 다운로드 전용 stage.
# downloader의 Python 패키지는 최종 이미지에 복사하지 않는다.
FROM python:3.12-slim@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9 AS camoufox
COPY --from=ghcr.io/astral-sh/uv:0.11.18@sha256:78bc42400d77b0678ba95765305c826652ed5431f399257271dda681d0318f03 /uv /usr/local/bin/uv
COPY --from=camoufox-version /camoufox-requirements.txt /camoufox-requirements.txt
RUN --mount=type=cache,target=/tmp/uv-cache \
    UV_CACHE_DIR=/tmp/uv-cache uv pip install --system -r /camoufox-requirements.txt

# read-only rootfs와 재시작마다 비워지는 $HOME 대신 /opt/camoufox에 설치한다.
# 런타임 entrypoint가 이 디렉토리를 $HOME/.cache/camoufox로 연결한다.
RUN HOME=/tmp XDG_CACHE_HOME=/opt python -m camoufox fetch

# ---------------------------------------------------------------------------
# Stage 1: builder — compiles the venv
# ---------------------------------------------------------------------------
FROM python:3.12-slim@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9 AS builder

# apt 보안 패치 레이어의 캐시 키. build.sh가 날짜를 넘겨 하루 1회 재실행시킨다.
# 이 값이 고정이면 아래 apt-get upgrade가 캐시에서 재사용되어 chromium 등의 패치가 적용되지 않는다.
ARG APT_REFRESH=0

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    : "apt refresh ${APT_REFRESH}" && \
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
FROM python:3.12-slim@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9

ARG APT_REFRESH=0
# 패치 전 APT 캐시가 재사용되더라도 취약한 Chromium으로 빌드하지 않는다.
ARG CHROMIUM_MIN_VERSION=156.0.8078.108-1~deb13u1

# Runtime-only: chromium engine + gosu + curl(HEALTHCHECK) + shared libs that the
# compiled wheels (poppler/heif/cairo) link against. Package names resolved from the
# -dev packages' runtime deps on debian (python:3.12-slim base).
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    : "apt refresh ${APT_REFRESH}" && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    chromium chromium-driver gosu curl ca-certificates git \
    libpoppler-cpp2 libpoppler147 libheif1 \
    libcairo2 libcairo-gobject2 \
    libfontconfig1 libfreetype6 libjpeg62-turbo libpng16-16t64 \
    # camoufox(패치 Firefox) 런타임 공유 라이브러리 (libxul.so NEEDED 기준, trixie 패키지명).
    # cairo/fontconfig/freetype은 위에서 이미 설치됨.
    libgtk-3-0t64 libgdk-pixbuf-2.0-0 libpango-1.0-0 libglib2.0-0t64 \
    libatk1.0-0t64 libasound2t64 libdbus-1-3 \
    libx11-6 libx11-xcb1 libxcb1 libxcb-shm0 libxcomposite1 libxcursor1 \
    libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 && \
    apt-get upgrade -y && \
    for package in chromium chromium-common chromium-driver; do \
        installed=$(dpkg-query -W -f='${Version}' "$package") && \
        dpkg --compare-versions "$installed" ge "$CHROMIUM_MIN_VERSION" || exit 1; \
    done && \
    # crashpad handler wrapper (same trick as single-stage image)
    printf '#!/bin/sh\nexec /usr/lib/chromium/chrome_crashpad_handler.real "$@" --database=/tmp/crashpad 2>/dev/null || true\n' \
        > /usr/lib/chromium/chrome_crashpad_handler.wrapper && \
    mv /usr/lib/chromium/chrome_crashpad_handler /usr/lib/chromium/chrome_crashpad_handler.real && \
    mv /usr/lib/chromium/chrome_crashpad_handler.wrapper /usr/lib/chromium/chrome_crashpad_handler && \
    chmod +x /usr/lib/chromium/chrome_crashpad_handler && \
    rm -rf /var/lib/apt/lists/*

# Runtime 의존성은 builder의 uv.lock으로 설치한다. 사용하지 않는 system pip는 제외한다.
RUN python -m pip uninstall --yes pip && rm -rf /usr/local/lib/python3.12/ensurepip

ARG USER_ID=1000
ARG USER_NAME=terzeron
RUN useradd -l -u $USER_ID $USER_NAME && \
    mkdir -p /app /app/backend /app/bin /app/utils /fma /xml \
        /home/$USER_NAME/.cache/pip /home/$USER_NAME/.local /home/$USER_NAME/.local/bin \
        /run/dbus && \
    chown -R $USER_NAME /app /fma /xml /home/$USER_NAME/.cache /home/$USER_NAME/.local

# Bring the prebuilt venv from the builder (no toolchain copied).
COPY --from=builder --chown=$USER_NAME /app/.venv /app/.venv

# camoufox 바이너리 + GeoIP DB(전용 stage에서 fetch). 런타임에 entrypoint.sh가
# $HOME/.cache/camoufox(platformdirs 해석 경로)로 symlink하여 재다운로드 없이 사용한다.
COPY --from=camoufox --chown=$USER_NAME /opt/camoufox /opt/camoufox

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
# 로그 asctime을 호스트와 같은 KST로 남긴다. 코드는 저장 시각에 UTC를 명시하므로 데이터에는 영향이 없다.
ENV TZ=Asia/Seoul
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
CMD ["uvicorn", "backend.main:app", "--workers", "1", "--host", "0.0.0.0", "--port", "8010", "--no-proxy-headers", "--log-level", "info", "--access-log", "--log-config", "/app/logging.conf"]
