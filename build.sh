#!/bin/bash

# Clean up unnecessary files before build
rm -rf -- */{nohup.out*,run.log*,.mypy_cache,__pycache__,.idea,.git}

docker build -f Dockerfile.backend --build-arg FM_BACKEND_PORT="$FM_BACKEND_PORT" -t terzeron/fm_backend . && \
docker tag terzeron/fm_backend:latest registry.terzeron.com/terzeron/fm_backend:latest && \
docker push registry.terzeron.com/terzeron/fm_backend:latest || exit 1

docker build -f Dockerfile.frontend -t terzeron/fm_frontend . && \
docker tag terzeron/fm_frontend:latest registry.terzeron.com/terzeron/fm_frontend:latest && \
docker push registry.terzeron.com/terzeron/fm_frontend:latest || exit 1

echo 'You should run the initialization script;'
echo 'python -c "from bin.db import DB; DB.create_all_tables()"'
echo 'python -c "from bin.problem_manager import ProblemManager; pm = ProblemManager(); pm.load_all()"'

