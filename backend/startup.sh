#!/bin/bash

if [ -f .env.development ]; then
    source .env.development
    if [ "$FM_DB_HOST" = "127.0.0.1" ]; then
        db_name="fm_db"
    else
        db_name="$FM_DB_HOST"
    fi
fi
env | grep -E "(FM_|WEB_|MSG_|MYSQL_|PYTHON)" | sort

pidfile="uvicorn.pid"
if [ -f "$pidfile" ]; then
    echo "Killing old process..."
    kill "$(cat $pidfile)" && rm -f "$pidfile"
    sleep 2
fi

if [ -e nohup.out ]; then
    mv nohup.out nohup.out.old
fi

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
        -v $(dirname $(pwd))/init.sql:/docker-entrypoint-initdb.d/init.sql \
        -v $(dirname $(pwd))/mysql_data_dir:/var/lib/mysql \
        --env-file ../.env \
        mysql:8.0.35
    echo "###### mysql is running ######"
    sleep 2
fi

docker ps

echo "###### run backend ######"
nohup uvicorn main:app --reload --workers=4 --port="$FM_BACKEND_PORT" &
echo "$!" > "$pidfile"
sleep 2
tail nohup.out

