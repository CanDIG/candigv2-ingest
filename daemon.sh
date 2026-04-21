#!/bin/bash

python daemon.py &
pid=$!

while true
do
    sleep 60
    restart_me=0 # if this is 1, respawn daemon and resave pid

    if [[ $(ps -p $pid | wc -l) == 1 ]]; then
        echo "Process $pid has terminated"
        restart_me=1
    fi

    if [[ $restart_me == 1 ]]; then
        echo "Restarting daemon"
        python daemon.py &
        pid=$!
    fi
done
