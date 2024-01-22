#!/bin/bash

if [ "$1" = "-r" ]; then
  echo "###### remove fm_backend ######"
  docker rm -f fm_backend

  echo "###### remove fm_frontend ######"
  docker rm -f fm_frontend

  echo "###### remove mysql ######"
  docker rm -f fm_db
  rm -rf $(pwd)/mysql_data_dir

  echo "###### remove network ######"
  docker network rm fm_network
fi

echo "###### make network ######"
if docker network ls | grep fm_network > /dev/null 2>&1; then
  echo "###### network is already created ######"
else
  docker network create fm_network
  echo "###### network is created ######"
fi

echo "###### run fm_db ######"
if docker inspect -f '{{.State.Running}}' fm_db | grep true > /dev/null 2>&1; then
  echo "###### fm_db is already running ######"
else
  docker pull mysql:8.0.35 > /dev/null
  docker run \
    --name fm_db \
    --network fm_network \
    -d \
    -p 13306:3306 \
    --user "$(id -u):$(id -g)" \
    -v "$(pwd)/init.sql:/docker-entrypoint-initdb.d/init.sql" \
    -v "$(pwd)/mysql_data_dir:/var/lib/mysql" \
    --env-file .env \
    mysql:8.0.35
  echo "###### mysql is running ######"
fi

echo "###### starting fm_frontend ######"
if docker inspect -f '{{.State.Running}}' fm_frontend | grep true > /dev/null 2>&1; then
  echo "###### fm_frontend is already running ######"
else
  docker run \
    --name fm_frontend \
    --network fm_network \
    -d \
    -p 8080:80 \
    terzeron/fm_frontend
  echo "###### fm_frontend is running ######"
fi

echo "###### run fm_backend ######"
if docker inspect -f '{{.State.Running}}' fm_backend | grep true > /dev/null 2>&1; then
  echo "###### fm_backend is already running ######"
else
  docker run \
    --name fm_backend \
    --network fm_network \
    -d \
    -p 8010:8010 \
    -v "$HOME/workspace/fma:/fma" \
    -v "$HOME/public_html/xml:/xml" \
    --env-file .env \
    terzeron/fm_backend
  echo "###### fm_backend is running ######"
fi

docker ps
