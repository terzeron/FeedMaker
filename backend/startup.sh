#!/bin/bash

pidfile="uvicorn.pid"
if [ -f "$pidfile" ]; then
    echo "Killing old process..."
    kill $(cat $pidfile)
    sleep 3
fi

echo "Starting service..."
nohup uvicorn main:app --port=8010 &
echo "$!" > "$pidfile"
sleep 2
