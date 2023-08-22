ARG venv_python
ARG alpine_version
FROM python:${venv_python}-alpine${alpine_version}

LABEL Maintainer="CanDIG Project"
LABEL "candigv2"="ingest_app"

USER root

RUN addgroup -S candig && adduser -S candig -G candig

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
    libffi-dev \
	git

RUN mkdir /ingest_app
WORKDIR /ingest_app

ADD ./requirements.txt /ingest_app/requirements.txt
RUN pip install -r requirements.txt

COPY . /ingest_app

RUN chmod +x ./run.sh
ENTRYPOINT ./run.sh
EXPOSE 1235


