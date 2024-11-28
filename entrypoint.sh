#!/usr/bin/env bash
mkdir -p $DAEMON_PATH/to_ingest
mkdir -p $DAEMON_PATH/results
bash /ingest_app/daemon.sh &

gunicorn server:app