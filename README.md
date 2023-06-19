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

### Ingest into Htsget

Create a text file that list all sample IDs available in a particular S3 bucket. The ingest script will find all files starting with that particular ID in that bucket; for example, specifying AB0001 will ingest, if available, AB0001.vcf.gz/tbi, AB0001.mutect2.vcf.gz/tbi, and AB0001_comparison.vcf.gz/tbi. The bucket should contain both bgzipped VCF files and their corresponding tabix index files.

Connecting the genomic IDs and files to patient clinical data will be handled during clinical data ingest; see below.

To make the genomic files accessible to the htsget server, run:

```bash
python htsget_s3_ingest.py --sample <sample>|--samplefile <samplefile> --dataset <dataset>  --awsfile <aws credentials> --endpoint <S3 endpoint> --bucket <S3 bucket> --prefix <optional, prefix for files in S3 bucket> --reference <reference genome, either hg37 or hg38>
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
Currently, the containerized version supports a two endpoints for ingesting a DonorWithClinicalData object and genomic data.
To run, ensure you have docker installed and CanDIGv2 running, then run the following commands:
```bash
docker build . --build-arg venv_python=3.10 --build-arg alpine_version=3.14 -t44 ingest_app
docker run -p 1235:1235 -e CANDIG_URL="$CANDIG_URL" VAULT_URL="$VAULT_URL" OPA_URL="$OPA_URL" --name candig-ingest --add-host candig.docker.internal:[YOUR LOCAL IP] ingest_app
```
(Note that VAULT_URL's host is often set as 0.0.0.0, which the container may not be able to access;
if so, set it to candig.docker.internal:8200.)


This will start a Docker container with a REST API for the ingest at localhost:1235. You can ingest a DonorWithClincalData object by POSTing JSON to localhost:1235/ingest_donor (an example is given in single_ingest.json, or you can simply copy the "results" key from a Katsu DonorWithClinicalData authorized query). 
Genomic data can be ingested from an S3 bucket at the /ingest_genomic endpoint, with the following JSON format:
```json
"dataset": "[dataset name]",
"endpoint": "[S3 URL]",
"bucket": "[S3 bucket name]",
"access": "[S3 bucket access username]",
"secret": "[S3 bucket access password]",
"samples": ["[sample name 1]", "[sample name 2]", ...] 
```
Make sure you include Authorization headers as well.