#!/usr/bin/env bash
export OPA_SECRET=$(cat /run/secrets/opa-service-token)
uwsgi /ingest_app/uwsgi.ini