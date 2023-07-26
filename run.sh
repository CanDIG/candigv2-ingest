#!/usr/bin/env bash
if [[ $0 == "TRUE" ]]; then
    export KATSU_TRAILING_SLASH="TRUE"
fi
uwsgi /ingest_app/uwsgi.ini