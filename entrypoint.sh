#!/usr/bin/env bash

if [[ -f "initial_setup" ]]; then
    mkdir -p $DAEMON_PATH/to_ingest
    mkdir -p $DAEMON_PATH/results
    echo "Initializing setup"
    python migrate.py
    if [[ $? -eq 0 ]]; then
        rm initial_setup
        echo "setup complete"
    else
        echo "!!!!!! INITIALIZATION FAILED, TRY AGAIN !!!!!!"
    fi
fi

bash /ingest_app/daemon.sh &

gunicorn -k uvicorn.workers.UvicornWorker server:app
