#!/bin/bash

cd "$FM_HOME_DIR"

env | grep -E "^(FM_|WEB_|MYSQL_)" | sort

pidfile="backend/uvicorn.pid"
if [ -f "$pidfile" ]; then
    echo "Killing old process..."
    kill "$(cat $pidfile)" && rm -f "$pidfile"
    sleep 2
fi

echo "###### run backend ######"
uvicorn backend.main:app --reload --port="$FM_BACKEND_PORT"

