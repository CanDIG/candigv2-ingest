ARG venv_python
FROM python:${venv_python}

ARG prod_environment=FALSE
ENV PROD_ENVIRONMENT=${prod_environment}

LABEL Maintainer="CanDIG Project"
LABEL "candigv2"="ingest_app"

USER root

RUN useradd -rm candig -U

RUN apt-get update && apt-get -y install vim

RUN mkdir /ingest_app
WORKDIR /ingest_app

ADD ./requirements.txt /ingest_app/requirements.txt
ADD ./requirements-container.txt /ingest_app/requirements-container.txt
RUN pip install -r requirements-container.txt

COPY . /ingest_app

RUN chmod +x ./run.sh

RUN chown -R candig:candig /ingest_app

USER candig

ENTRYPOINT ./run.sh
EXPOSE 1235
