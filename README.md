# candigv2-ingest

Ingest data into the CanDIGv2 stack. This repository assumes that you have a functional instance of CanDIGv2.

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

Before you can ingest the clinical data, you need to format your data into the json ingest format using the [clinical_ETL](https://github.com/CanDIG/clinical_ETL_data) and put it in the katsu `data` folder, then set the environment variable `MOH_DATA_LOCATION`:

NOTE: if you just want to use the [synthetic data](https://github.com/CanDIG/katsu/tree/develop/chord_metadata_service/mohpackets/data/small_dataset/synthetic_data), you can skip this step.

```bash
export MOH_DATA_LOCATION=path/to/moh/data/
```

Run katsu's moh_ingest.py script. This will represent severals options:

1. Run check: check if the you are ready to ingest the data.
2. Ingest data: import the data into katsu
3. Clean data: reset the database to the clean state. Use this if you want to start over. WARNING: be careful in production environment, as it irreversibe.

You can also run the script with the `-choice` to skip the menu and go straight to the choice you want.

```bash
python moh_ingest.py -choice 2
```
