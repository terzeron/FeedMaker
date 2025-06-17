#!/bin/bash

if [ -d CartoonSplit ]; then
    (cd CartoonSplit && git stash > /dev/null && git pull > /dev/null && git stash pop > /dev/null)
else
    git clone https://github.com/terzeron/CartoonSplit > /dev/null
fi

rm -rf -- */{nohup.out*,run.log*,.mypy_cache,__pycache__,.idea,.git} CartoonSplit/test
docker build -f Dockerfile.backend --build-arg FM_BACKEND_PORT="$FM_BACKEND_PORT" -t terzeron/fm_backend . && \
docker tag terzeron/fm_backend:latest registry.terzeron.com/terzeron/fm_backend:latest && \
docker push registry.terzeron.com/terzeron/fm_backend:latest

rm -rf CartoonSplit

docker build -f Dockerfile.frontend -t terzeron/fm_frontend . && \
docker tag terzeron/fm_frontend:latest registry.terzeron.com/terzeron/fm_frontend:latest && \
docker push registry.terzeron.com/terzeron/fm_frontend:latest
