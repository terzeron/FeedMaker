#!/bin/bash

# Enable Docker BuildKit for better performance and features
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
export USER_ID=$(id -u)
export USER_NAME=$(whoami)

# Clean up unnecessary files before build
rm -rf -- */{nohup.out*,run.log*,.mypy_cache,__pycache__,.idea,.git}

docker build -f Dockerfile.backend --build-arg FM_BACKEND_PORT="$FM_BACKEND_PORT" -t terzeron/fm_backend . && \
docker tag terzeron/fm_backend:latest registry.terzeron.com/terzeron/fm_backend:latest && \
docker push registry.terzeron.com/terzeron/fm_backend:latest || exit 1

docker build -f Dockerfile.frontend -t terzeron/fm_frontend . && \
docker tag terzeron/fm_frontend:latest registry.terzeron.com/terzeron/fm_frontend:latest && \
docker push registry.terzeron.com/terzeron/fm_frontend:latest || exit 1

echo
echo 'You should run the initialization script;'
echo 'python -c "from bin.db import DB; DB.create_all_tables()"'
echo 'python -c "from bin.problem_manager import ProblemManager; pm = ProblemManager(); pm.load_all()"'

echo
echo 'You might deploy the containers;'
echo 'kubectl apply -f ~/k8s/feedmaker/fm-deployment.yml'
echo 'kubectl rollout restart deployment fm-backend -n feedmaker'
echo 'kubectl rollout restart deployment fm-frontend -n feedmaker'
