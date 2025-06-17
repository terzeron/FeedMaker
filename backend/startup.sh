#!/bin/bash

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
absolute_path="$(dirname "$SCRIPT_PATH")"
cd "$absolute_path"
pwd

export $(grep -v '^#' .env.development | xargs)
env | grep -E "^(FM_|WEB_|MYSQL_)" | sort

db_name="fm_db"

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
    mkdir -p "$absolute_path/mysql_data_dir" > /dev/null 2>&1
    chmod 755 "$absolute_path/mysql_data_dir" > /dev/null 2>&1

    docker rm fm_db > /dev/null 2>&1
    docker pull mysql:8.0.35 > /dev/null

    echo "docker run --name $db_name -d -p $FM_DB_PORT:3306 --network fm_network --user $(id -u):$(id -g) -v $absolute_path/mysql_data_dir:/var/lib/mysql --env-file .env.development mysql:8.0.35"
    docker run \
        --name "$db_name" \
        -d \
        -p "$FM_DB_PORT":3306 \
        --network fm_network \
        --user "$(id -u):$(id -g)" \
        -v "$absolute_path/mysql_data_dir:/var/lib/mysql" \
        --env-file .env.development \
        mysql:8.0.35
    echo "###### mysql is running ######"
    sleep 2
fi

docker ps

echo "###### run backend ######"
#nohup uvicorn backend.main:app --reload --workers=4 --port="$FM_BACKEND_PORT" &
#echo "$!" > "$pidfile"
#sleep 2
#tail nohup.out
uvicorn backend.main:app --reload --port="$FM_BACKEND_PORT"

