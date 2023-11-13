ARG venv_python
FROM python:${venv_python}

ARG prod_environment=FALSE
ENV PROD_ENVIRONMENT=${prod_environment}

LABEL Maintainer="CanDIG Project"
LABEL "candigv2"="ingest_app"

USER root

RUN useradd -r candig -U

RUN mkdir /ingest_app
WORKDIR /ingest_app

ADD ./requirements.txt /ingest_app/requirements.txt
RUN pip install -r requirements.txt

COPY . /ingest_app

RUN chmod +x ./run.sh
ENTRYPOINT ./run.sh
EXPOSE 1235
