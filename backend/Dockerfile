FROM python:3.12-slim

# root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpoppler-dev libpoppler-cpp-dev libheif-dev libcairo2-dev \
    build-essential git curl unzip gnupg ca-certificates chromium chromium-driver && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ARG USER_ID=1000
ARG USER_NAME=terzeron
RUN useradd -u $USER_ID $USER_NAME && \
    mkdir -p /app /app/backend /app/bin /app/utils /fma /xml /home/$USER_NAME/.cache/pip /home/$USER_NAME/.local /home/$USER_NAME/.local/bin /run/dbus /tmp/logs /app/logs && \
    chown -R $USER_NAME /app /fma /xml /home/$USER_NAME/.cache/pip /home/$USER_NAME/.local /home/$USER_NAME/.local /tmp/logs /app/logs

RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    cp /root/.local/bin/uv /usr/local/bin/

# user(1000)
USER $USER_NAME
WORKDIR /app

ENV UV_SYSTEM_PYTHON=1 UV_LINK_MODE=copy UV_PYTHON=python3.12
COPY pyproject.toml uv.lock /app/
RUN HOME=/tmp XDG_CACHE_HOME=/tmp/.cache UV_CACHE_DIR=/tmp/uv-cache \
    uv sync --locked --no-editable

COPY logging.conf /app
COPY backend /app/backend
COPY bin /app/bin
COPY utils /app/utils

RUN git clone https://github.com/terzeron/CartoonSplit /app/CartoonSplit && \
    rm -rf /app/CartoonSplit/.git /app/CartoonSplit/test

VOLUME /fma
VOLUME /xml
VOLUME /logs

ENV CARTOON_SPLIT_HOME_DIR="/app/CartoonSplit"
ENV PATH="/app/.venv/bin:/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:/home/$USER_NAME/.local/bin:/app/bin:/app/utils"
ENV PYTHONPATH="/app"
ARG FM_BACKEND_DEFAULT_PORT=8010
ENV FM_BACKEND_PORT=$FM_BACKEND_DEFAULT_PORT

EXPOSE $FM_BACKEND_PORT

CMD ["sh", "-c", "uvicorn backend.main:app --workers 1 --host 0.0.0.0 --port 8010 --log-level debug --access-log --log-config /app/logging.conf"]
