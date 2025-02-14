# candigv2-ingest

Ingest data into the [CanDIGv2 stack](https://github.com/CanDIG/CanDIGv2). This repository assumes that you have a functional instance of the [CanDIGv2 software stack](https://github.com/CanDIG/CanDIGv2).

This repository can either be run standalone or as a Docker container.

## Step-by-step guide to ingesting data into the CanDIG platform

Please visit our [Documentation website](https://candig.github.io/CanDIGv2) for a full run-down of the data ingest process.

## Managing user roles using the ingest API

Please visit our [Documentation website](https://candig.github.io/CanDIGv2) for detailed documentation about how user roles are managed in CanDIG via the API. The [openapi schema](ingest_openapi.yaml) can also be consulted for a definitive guide to endpoints. This is also available [via our documentation website here](https://candig.github.io/CanDIGv2/technical/ingest-api/operations/ingest_operationsget_service_info/) or [swaggerized here](https://editor.swagger.io/?url=https://raw.githubusercontent.com/CanDIG/candigv2-ingest/develop/ingest_openapi.yaml).

## Run as Docker Container
The containerized version runs the API as specified above within a Docker container (which is how this repository is used in the CanDIGv2 stack).
To run, ensure you have docker installed and CanDIGv2 running, then run the following commands:
```bash
docker build . --build-arg venv_python=3.10 --build-arg alpine_version=3.14 -t ingest_app
docker run -p 1236:1235 -e CANDIG_URL="$CANDIG_URL" -e KEYCLOAK_PUBLIC_URL="$KEYCLOAK_PUBLIC_URL" -e VAULT_URL="http://candig.docker.internal:8200" -e CANDIG_CLIENT_ID="$CANDIG_CLIENT_ID" -e CANDIG_CLIENT_SECRET="$CANDIG_CLIENT_SECRET" --name candig-ingest-dev --add-host candig.docker.internal:[YOUR LOCAL IP] ingest_app
```

Also, Note that VAULT_URL's host is often set as 0.0.0.0, which the container may not be able to access;
if so, set it to candig.docker.internal:8200 (or whatever your vault port is).


This will start a Docker container with a REST API for the ingest at localhost:1236. Then follow the same API instructions above.

(Note: on the CanDIGv2 repo, the service runs on port 1235; it is run as 1236 locally in these instructions to ensure there is no
interference while testing.)


## Testing

To test candigv2-ingest, from the repo directory, simply run the following command:

```commandline
pytest
```

## Generating json files for test ingest

The script `generate_test_data.py` can be used to generate a json files for ingest from an the CanDIG MOHCCN sythetic data repo. The script automatically clones the [`mohccn-synthetic-data`](https://github.com/CanDIG/mohccn-synthetic-data) repo and converts the small dataset, saving the json files needed for ingest in the `tests` directory as `small_dataset_clinical_ingest.json` and `small_dataset_genomic_ingest.json`. It then deletes the cloned repo. If validation of the dataset fails, it saves the validation results to the `tests/` directory as `small_dataset_clinical_ingest_validation_results.json`. If you are running this container as part of the CanDIGv2 stack, this data generation is run as part of the `make compose-candig-ingest` step, so the files may already exist in the `lib/candig-ingest/candigv2-ingest/tests` directory.

To run:

* Set up a virtual environment and install requirements (if you haven't already). If running inside the ingest docker container, this shouldn't be needed.
```commandline
pip install -r requirements.txt
```
* Run the script with the desired output location and an optional prefix for the identifiers

Usage:
```commandline
python generate_test_data.py -h
usage: generate_test_data.py [-h] [--prefix PREFIX] --tmp

A script that copies and converts data from mohccn-synthetic-data for ingest into CanDIG platform.

options:
  -h, --help       show this help message and exit
  --prefix PREFIX  optional prefix to apply to all identifiers
  --TMP TMP  Directory to temporarily clone the mohccn-synthetic-data repo.

```
