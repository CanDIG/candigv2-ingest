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

## Set environment variables

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

### Store locally in htsget
If necessary, genomic samples can be loaded directly from the htsget container's internal storage. Simply `docker cp` the sample files somewhere into the container and proceed below with the instructions for local ingest.

### Ingest into Htsget

Genomic samples should be specified in a JSON list of dictionaries, providing their genomic ID and optionally associated clinical IDs and filenames.
The respective keys for these attributes are genomic_id, clinical_id, and files; if filenames are specified, the files key
should be another dictionary with the keys "index" and "sample", which specify the genomic index file and variation file respectively.
For example:

```json
[
  {"genomic_id": "HG00096", "clinical_id": null, "files": null}, 
  {"genomic_id": "HG00097", "clinical_id": "DONOR_1", "files": {"sample": "HG97_SAMPLE.vcf.gz", "index": "HG97_SAMPLE.vcf.gz.tbi"}}
  {"genomic_id": "HG00099", "clinical_id": null, "files": null}
]
```
If files are stored in an S3 Bucket, the location of the files should be provided using the prefix argument in htsget_ingest, and only filenames should be given in the JSON.
For local ingest, absolute paths within the container should be provided for filenames.

If filenames are not provided, the ingest will search for any variation/index files in the container prefixed with the genomic_id.
For local ingest, filenames must be specified.

To ingest using an S3 container, once the files have been added, you can run the htsget_ingest.py script:
```bash
python htsget_ingest.py --samplefile [JSON-formatted sample list as specified] --dataset <dataset>  --awsfile <aws credentials> --endpoint <S3 endpoint> --bucket <S3 bucket> --prefix <optional, prefix for files in S3 bucket> --reference <reference genome, either hg37 or hg38> --indexing <optional, force re-index>
```

To ingest from the htsget container, you can use the -local flag:
```bash
python htsget_ingest.py -local --samplefile [JSON-formatted sample list] --dataset <dataset>  --reference <reference genome, either hg37 or hg38> --indexing <optional, force re-index>
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

Run katsu_ingest.py script. This will represent severals options:

1. Run check: check if ingest is possible
2. Ingest data: import the data into katsu
3. Clean data: reset the database to the clean state. Use this if you want to start over. WARNING: be careful in production environment, as it irreversibe.

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


This will start a Docker container with a REST API for the ingest at localhost:1235. You can ingest a DonorWithClincalData object by POSTing JSON to localhost:1236/ingest_donor (an example is given in single_ingest.json, or you can simply copy the "results" key from a Katsu DonorWithClinicalData authorized query). 
Genomic data can be ingested from an S3 bucket at the /ingest_genomic endpoint, with the following JSON format:
```json
{
    "dataset": "[dataset name]",
    "endpoint": "[S3 URL]",
    "bucket": "[S3 bucket name]",
    "access": "[S3 bucket access username]",
    "secret": "[S3 bucket access password]",
    "samples": [JSON formatted samples, see command line instructions],
    "prefix": "[S3 prefix, optional]",
    "reference": "[Reference genome, either hg37 or hg38, optional]",
    "indexing": "[Force reindexing (true/false), optional]",
    "local": true/false (whether to ingest from htsget local storage instead of s3)
}
```
Make sure you include Authorization headers as well. Both endpoints take refresh tokens, as a header with the key `{"Authorization": "Bearer [refresh token]"}`.

(Note: on the CanDIGv2 repo, the service runs on port 1235; it is run as 1236 locally in these instructions to ensure there is no
interference while testing.)