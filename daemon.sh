#!/bin/bash

TOUCH_FILE=$DAEMON_PATH/last_touch.txt

python daemon.py &
pid=$!

# This effectivley puts a time limit on the acceptable length of a program.  When the daemon restarts, ingestion of the whole JSON restarts.
# 36h is a best estimate based on the largest programs (currently 1200 - 1420 donours, which could take ~18-24h to ingest).
interval=$((60*60*36)) # 36h. The length of time to wait for updates in TOUCH_FILE

while true
do
    sleep 60
    restart_me=0 # if this is 1, respawn daemon and resave pid

    if [[ $(ps -p $pid | wc -l) == 1 ]]; then
        echo "Process $pid has terminated"
        restart_me=1
    fi

    # check to see if the touch file exists and is still updating
    if [[ -f $TOUCH_FILE ]]; then
        now=$(date +%s)
        last_touch=$(cat $TOUCH_FILE)
        echo "Ingest in process...last updated" $(($now - $last_touch)) "seconds ago"
        if (($now - $last_touch > $interval)); then
            echo "Last update was more than" $interval "seconds ago"
            kill $pid
            restart_me=1
        fi
    fi

    if [[ $restart_me == 1 ]]; then
        echo "Restarting daemon"
        if [[ -f $TOUCH_FILE ]]; then
            rm $TOUCH_FILE
        fi
        python daemon.py &
        pid=$!
    fi
done
