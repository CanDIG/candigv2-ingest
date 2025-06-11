#!/usr/bin/env bash

if [[ -f "initial_setup" ]]; then
    mkdir -p $DAEMON_PATH/to_ingest
    mkdir -p $DAEMON_PATH/results
    python migrate.py
    rm initial_setup
fi

bash /ingest_app/daemon.sh &

gunicorn -k uvicorn.workers.UvicornWorker server:app
