#!/bin/bash

pidfile="uvicorn.pid"
if [ -f "$pidfile" ]; then
    echo "Killing old process..."
    kill "$(cat $pidfile)"
    sleep 3
fi

rm -f nohup.out
echo "Starting service..."
nohup uvicorn main:app --reload --workers=4 --port=8000 &
echo "$!" > "$pidfile"
sleep 2
tail nohup.out
