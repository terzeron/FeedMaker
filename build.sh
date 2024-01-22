#!/bin/bash

if [ -d CartoonSplit ]; then
    (cd CartoonSplit && git stash && git pull && git stash pop)
else
    git clone https://github.com/terzeron/CartoonSplit
fi

rm -rf */{nohup.out*,run.log*,.mypy_cache,__pycache__,.idea,.git} CartoonSplit/test
docker build -f Dockerfile.backend -t terzeron/fm_backend .

(cd frontend && npm install -y && npx browserslist@latest -y && npm run build)
docker build -f Dockerfile.frontend -t terzeron/fm_frontend .
