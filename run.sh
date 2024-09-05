#!/usr/bin/env bash
mkdir -p $DAEMON_PATH/to_ingest
mkdir -p $DAEMON_PATH/results
python /ingest_app/daemon.py &

uwsgi /ingest_app/uwsgi.ini