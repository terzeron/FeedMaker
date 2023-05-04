#!/bin/bash

pidfile="uvicorn.pid"
if [ -f "$pidfile" ]; then
    echo "Killing old process..."
    kill "$(cat $pidfile)"
    sleep 3
fi

mv nohup.out nohup.out.old
echo "Starting service..."
nohup uvicorn main:app --reload --workers=4 --port=8010 &
echo "$!" > "$pidfile"
sleep 2
tail nohup.out
