ARG venv_python
ARG alpine_version
FROM python:${venv_python}-alpine${alpine_version}

LABEL Maintainer="CanDIG Project"
LABEL "candigv2"="ingest_app"

USER root

RUN apk update
RUN apk add --no-cache \
	autoconf \
	automake \
	make \
	gcc \
	bash \
	build-base \
	musl-dev \
	zlib-dev \
	bzip2-dev \
	xz-dev \
	linux-headers \
	pcre-dev \
	git

RUN mkdir /ingest_app
WORKDIR /ingest_app
COPY . /ingest_app

RUN pip install --no-cache-dir -r /ingest_app/requirements.txt

ENTRYPOINT ["bash", "./run.sh"]
EXPOSE 1235

