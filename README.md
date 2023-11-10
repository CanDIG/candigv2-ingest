# candigv2-ingest

Ingest data into the CanDIGv2 stack. This repository assumes that you have a functional instance of CanDIGv2.
This repository can either be run standalone or as a Docker container.

## What you'll need

* A valid user for CanDIGv2 that has site administration credentials.
* List of users that will have access to this dataset.
* Clinical data, saved as either an Excel file or as a set of csv files.
* Genomic data files in vcf format.
* File map of genomic files in a csv file, linking genomic sample IDs to the clinical samples.
* (if needed) Credentials for s3 endpoints: url, access ID, secret key.
* Reference genome used for the variant files.
* Manifest and mappings for clinical_ETL conversion.

## Setup
Run the following:
```bash
pip install -r requirements.txt
git submodule update --init --recursive
```

### Set environment variables

* CANDIG_URL (same as TYK_LOGIN_TARGET_URL, if you're using CanDIGv2's example.env)
* KEYCLOAK_PUBLIC_URL
* CANDIG_CLIENT_ID
* CANDIG_CLIENT_SECRET
* CANDIG_SITE_ADMIN_USER
* CANDIG_SITE_ADMIN_PASSWORD

For convenience, you can generate a file `env.sh` from your CanDIGv2 repo:

```bash
cd CanDIGv2
python settings.py
source env.sh
```

## How to use the ingest
candigv2-ingest can be used as either a command-line tool, a local API server or a docker container. To ingest from a UI, see the [CanDIG Data Portal](https://github.com/CanDIG/candig-data-portal). To run the command line scripts, set your environment variables and follow the command line instructions in the sections below. To use the local API, set your environment variables, run `python app.py`, and follow the API instructions in the sections below. The API will be available at localhost:1236. A swagger UI is also available at /ui. Docker instructions can be found at the bottom of the README. To authorize yourself for these endpoints, you will need to set the Authorization header to a keycloak bearer token (in the format "Bearer ..." without the quotes).


## Authorizing users for the new dataset
### NOTE: OPA ingest is currently not functional, so these instructions will not work.
Create a new access.json file:

```bash
python opa_ingest.py --dataset <dataset> --userfile <user file> > access.json
```

Alternately, you can add a single user:

```bash
python opa_ingest.py --dataset <dataset> --user <user email> > access.json
```

If you're running OPA in the CanDIGv2 Docker stack, you should copy the file to the Docker volume to persist the change between restarts:

```bash
docker cp access.json candigv2_opa_1:/app/permissions_engine/access.json
```

Restart the OPA container to take effect

## Ingest clinical data
Note: To upload a DonorWithClinicalData object, you should produce one using the [CanDIG ETL](https://github.com/CanDIG/clinical_ETL_code), then store its result in a JSON file under the key "donors". See single_ingest.json for an example.

### Command line
Before you can ingest the clinical data, you need to format your data into the json ingest format using the [clinical_ETL](https://github.com/CanDIG/clinical_ETL_data) and put it in the katsu `data` folder, then set the environment variable `CLINICAL_DATA_LOCATION`:

```bash
export CLINICAL_DATA_LOCATION=path/to/clinical/data/
```

NOTE: if you want to skip ETL process and use ready-made [synthetic data](https://github.com/CanDIG/katsu/tree/develop/chord_metadata_service/mohpackets/data/small_dataset/synthetic_data), set the path to:

```bash
export CLINICAL_DATA_LOCATION=https://raw.githubusercontent.com/CanDIG/katsu/develop/chord_metadata_service/mohpackets/data/small_dataset/synthetic_data/
```

Reload the environment variables:

```bash
source env.sh
```

Run katsu_ingest.py script:

```bash
python katsu_ingest.py
```

### API
The clinical ingest API runs at /ingest/clinical_donors. Simply send a request with an authorized bearer token and a JSON body with your DonorWithClinicalData object. See the swagger UI/schema for the response format.


## Ingest genomic files

**First**, ensure that the relevant clinical data is ingested, as this must be completed before your genomic data is ingested.

### Genomic file preparation

Files need to be in vcf or vcf.gz format.

* If .tbi files do not exist, create them.

### Store in S3-compatible system

<blockquote><details><summary>How do I move files into an S3-type bucket?</summary>
Ingest files into S3-compatible stores one endpoint/bucket at a time.

```bash
python s3_ingest.py --sample <sample>|--samplefile <samplefile> --endpoint <S3 endpoint> --bucket <S3 bucket> --awsfile <aws credentials>
```

</details></blockquote>


#### Add S3 credentials to vault
This can be done through the /add-s3-credential API endpoint. Simply provide the endpoint, bucket name, access key and secret key as the JSON body:
```json
{
	"endpoint": "candig.docker.internal:9000",
	"bucket": "mohccndata",
	"access_key": "admin",
	"secret_key": "BsjbFTCQ8TpKVRj9euQEsQ"
}
```
Your bucket will now be usable for htsget ingest.

### Store locally in htsget
If necessary, genomic samples can be loaded directly from the htsget container's internal storage. Simply `docker cp` the sample files somewhere into the container and prefix your access_method with file:// instead of s3:// (see below).

### Ingest into Htsget

Genomic samples should be specified in a JSON dictionary:
```json
{
	"access_method": "s3://candig.docker.internal:9000/dir",
	"genomic_id": "HG00096.vcf.gz",
	"index": "tbi",
  "samples": [
    {
      "sample_name_in_file": "TUMOR",
      "sample_registration_id": "SAMPLE_REGISTRATION_1"
    }
  ]
}
```
“genomic_id” is the filename of the variation file (e.g. HG00096.vcf.gz, HG00096.bam). Access methods can either be of the format s3://[endpoint]/[bucket name] or file://[directory relative to root on htsget container]. sample_registration_id(s) are the (mandatory) links to clinical sample_registrations.
"index" is the file extension of the index file for the variation; for instance, "tbi" or "crai".
If an S3 bucket access method is provided, assuming you have properly added the S3 credentials to vault (see above), the service will scan the S3 bucket to ensure the relevant files are present.
This will not occur for files local/mounted to htsget, so ensure they are present beforehand.

### Command line
To ingest using an S3 container, once the files have been added, you can run the htsget_ingest.py script:
```bash
python htsget_ingest.py --samplefile [JSON-formatted sample data as specified] --dataset <clinical dataset> --reference <reference genome, either hg37 or hg38> --indexing <optional, force re-index>
```

### API
Use the /ingest/moh_variants/[program_id] endpoint with the proper Authorization headers and your genomic JSON as specified above for the body to ingest and link to the clinical dataset program_id.

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
