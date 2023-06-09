ARG venv_python
ARG alpine_version
FROM python:${venv_python}-alpine${alpine_version}

LABEL Maintainer="CanDIG Project"
LABEL "candigv2"="ingest_app"

USER root

RUN apk update
RUN apk add --no-cache git

RUN mkdir /ingest_app
WORKDIR /ingest_app
COPY . /ingest_app

RUN pip install --no-cache-dir -r /ingest_app/requirements.txt

ENTRYPOINT ["python", "/ingest_app/app.py"]
EXPOSE 1235


