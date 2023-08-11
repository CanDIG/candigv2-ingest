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

## Authorizing users for the new dataset

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

## Ingest genomic files

### Genomic file preparation

Files need to be in vcf or vcf.gz format.

* If .tbi files do not exist, create them.

### Store in S3-compatible system

* Save the S3 credentials to a file in the format of `more ~/.aws/credentials` (please list only one credential in the file; the ingest will only process the first credential it finds.).

```bash
[default]
aws_access_key_id = xxxxx
aws_secret_access_key = xxxxx
```

<blockquote><details><summary>How do I move files into an S3-type bucket?</summary>
Ingest files into S3-compatible stores one endpoint/bucket at a time.

```bash
python s3_ingest.py --sample <sample>|--samplefile <samplefile> --endpoint <S3 endpoint> --bucket <S3 bucket> --awsfile <aws credentials>
```

</details></blockquote>

## Add S3 credentials to vault
This can be done through the /add-s3-credential API endpoint. Simply provide the endpoint, bucket name, access key and secret key as the JSON body:
{
	"endpoint": "candig.docker.internal:9000",
	"bucket": "mohccndata",
	"access_key": "admin",
	"secret_key": "BsjbFTCQ8TpKVRj9euQEsQ"
}
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

To ingest using an S3 container, once the files have been added, you can run the htsget_ingest.py script:
```bash
python htsget_ingest.py --samplefile [JSON-formatted sample data as specified] --dataset <dataset> --reference <reference genome, either hg37 or hg38> --indexing <optional, force re-index>
```

## Ingest clinical data

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

Run katsu_ingest.py script. This will represent several options:

1. Run check: check if ingest is possible
2. Ingest data: import the data into katsu
3. Clean data: reset the database to the clean state. Use this if you want to start over. WARNING: be careful in production environment, as it irreversible.
4. Ingest DonorWithClinicalData: Ingest a DonorWithClinicalData object into Katsu - CLINICAL_DATA_LOCATION should be a single JSON file

You can also run the script with the `-choice` to skip the menu and go straight to the choice you want.

```bash
python katsu_ingest.py -choice 2
```

## Run as Docker Container
Currently, the containerized version supports two endpoints for ingesting a DonorWithClinicalData object and genomic data.
To run, ensure you have docker installed and CanDIGv2 running, then run the following commands:
```bash
docker build . --build-arg venv_python=3.10 --build-arg alpine_version=3.14 -t ingest_app
docker run -p 1236:1235 -e CANDIG_URL="$CANDIG_URL" -e KEYCLOAK_PUBLIC_URL="$KEYCLOAK_PUBLIC_URL" -e VAULT_URL="http://candig.docker.internal:8200" -e CANDIG_CLIENT_ID="$CANDIG_CLIENT_ID" -e CANDIG_CLIENT_SECRET="$CANDIG_CLIENT_SECRET" --name candig-ingest-dev --add-host candig.docker.internal:[YOUR LOCAL IP] ingest_app
```
If your Katsu install uses trailing slashes at the end of endpoints (e.g. `/katsu/v2/ingest/programs/`), append `--build-arg katsu_trailing_slash=TRUE` to the `docker build` command above. This is stored in the environment variable KATSU_TRAILING_SLASH so if you are running locally just set that environment variable.

Also, Note that VAULT_URL's host is often set as 0.0.0.0, which the container may not be able to access;
if so, set it to candig.docker.internal:8200 (or whatever your vault port is).


This will start a Docker container with a REST API for the ingest at localhost:1235. You can ingest a DonorWithClincalData object by POSTing JSON to localhost:1236/ingest/clinical_donors (an example is given in single_ingest.json).

Genomic data can be ingested at the /ingest/moh_variants/{program ID} endpoint, where program_id is a cohort ID to add the variant to. This takes the same JSON body as specified in the htsget ingest section above.

Make sure you include Authorization headers as well. Both endpoints take refresh tokens, as a header with the key `{"Authorization": "Bearer [refresh token]"}`.

(Note: on the CanDIGv2 repo, the service runs on port 1235; it is run as 1236 locally in these instructions to ensure there is no
interference while testing.)