#!/bin/bash

source backend/.env.development
env | grep -E "(FM_|WEB_|MSG_|MYSQL_|PYTHON)" | sort

db_name="fm_db"
absolute_parent_dir="$(dirname $(pwd))"

pidfile="uvicorn.pid"
if [ -f "$pidfile" ]; then
    echo "Killing old process..."
    kill "$(cat $pidfile)" && rm -f "$pidfile"
    sleep 2
fi

if [ -e nohup.out ]; then
    mv nohup.out nohup.out.old
fi

echo "###### create network ######"
docker network create fm_network > /dev/null 2>&1 || echo "Network 'fm_network' already exists."

if [ "$1" = "-r" ]; then
    echo "###### remove DB server ######"
    if docker inspect "$db_name" > /dev/null; then
        docker rm -f "$FM_DB_HOST"
        rm -rf $(dirname $(pwd))/mysql_data_dir
    fi
fi

if docker inspect -f '{{.State.Running}}' "$db_name" | grep true > /dev/null 2>&1; then
    echo "###### DB server is already running ######"
else
    echo "###### run DB server ######"
    docker pull mysql:8.0.35 > /dev/null
    docker run \
        --name "$db_name" \
        -d \
        -p "$FM_DB_PORT":3306 \
        --network fm_network \
        --user "$(id -u):$(id -g)" \
        -v "absolute_parent_dir"/init.sql:/docker-entrypoint-initdb.d/init.sql \
        -v "absolute_parent_dir"/mysql_data_dir:/var/lib/mysql \
        --env-file .env \
        mysql:8.0.35
    echo "###### mysql is running ######"
    sleep 2
fi

docker ps

echo "###### run backend ######"
nohup uvicorn backend.main:app --reload --workers=4 --port="$FM_BACKEND_PORT" &
echo "$!" > "$pidfile"
sleep 2
tail nohup.out

