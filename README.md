# candigv2-ingest
Ingest data into the CanDIGv2 stack. This repository assumes that you have a functional instance of CanDIGv2.

## What you'll need:
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

## Ingest genomic files
### Genomic file preparation:
Files need to be in vcf or vcf.gz format.
* If .tbi files do not exist, create them.

### Store in S3-compatible system:
* Save the S3 credentials to a file in the format of `more ~/.aws/credentials` (please list only one credential in the file; the ingest will only process the first credential it finds.).

```
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
### Transform raw data into mcodepacket format
You'll need to generate a mapping file using the clinical_ETL tool to translate your raw clinical data into an mcodepacket-compatible format. Instructions about use of the clinical_ETL tool can be found at https://github.com/CanDIG/clinical_ETL.

In order to connect genomic sample IDs to clinical sample IDs, you'll need to include a mapping function for the mcodepacket's genomics_reports schema:

```
"genomics_report.extra_properties", {mcode.connect_variant("your_genomic_id")}
```

```python
def connect_variant(mapping):
    genomic_id = mappings.single_val({"GenomicID": mapping["your_genomic_id"]})
    genomic_file_ids = [
        genomic_id, # if there's a genomic_id.vcf.gz
        f"{genomic_id}.mutect2", # if there is a mutect analysis
        f"{genomic_id}_other_analysis"
    ]
    if genomic_id is None:
        return None
    return {
        "genomic_id": genomic_id, 
        "genomic_file_ids": genomic_file_ids
    }
```

Once you've written your mapper, map your data to mcodepackets:
```bash
python clinical_ETL/CSVConvert.py --input <directory of clinical csv files> --mapping <mapping manifest file>
```

### Ingest clinical data into katsu, CanDIG's clinical data server
Copy it to the katsu server, so that it is locally accessible:
```bash
docker cp input.json candigv2_chord-metadata_1:input.json
```

Then run the ingest tool:
```bash
python katsu_ingest.py --dataset $(DATASET) --input /input.json
```

As a quick sanity check, there is a simple little `katsu_status.py` script that will tell you how many
projects, datasets, and individuals are in the katsu at `$CANDIG_URL`.

After installation, you should be able to access the synthetic dataset:

* Get a user token, where the values for the data parameters are found in the files in tmp/secrets:

```
curl -X "POST" "http://auth.docker.localhost:8080/auth/realms/candig/protocol/openid-connect/token" \
     -H 'Content-Type: application/x-www-form-urlencoded; charset=utf-8' \
     --data-urlencode "client_id=local_candig" \
     --data-urlencode "client_secret=<value in $CANDIG_HOME/tmp/secrets/keycloak-client-local_candig-secret>" \
     --data-urlencode "grant_type=password" \
     --data-urlencode "username=<value in $CANDIG_HOME/tmp/secrets/keycloak-test-user>" \
     --data-urlencode "password=<value in $CANDIG_HOME/tmp/secrets/keycloak-test-user-password>" \
     --data-urlencode "scope=openid"
```

* You should see the dataset "mcode-synthetic" as part of the response for:

```
curl "http://docker.localhost:5080/katsu/api/datasets" \
     -H 'Authorization: Bearer <token>
``` 

* You should also be able to access all of the samples in the mcode-synthetic dataset via htsget if you're logged in as that user. If you're logged in as a different user (for example, the user specified in `$CANDIG_HOME/tmp/secrets/keycloak-test-user2`), you should get 403s. If you're not logged in at all, you'll get 401s.

```
curl "http://docker.localhost:3333/htsget/v1/variants/NA20787" \
     -H 'Authorization: Bearer <access_token>'
```

## Ingest clinical data into katsu MoH

Before you can ingest the clinical data, you need to obtain the data from the [clinical_ETL](https://github.com/CanDIG/clinical_ETL_data) and put it in the `data` folder, then set the environment variable `MOH_DATA_LOCATION`:

NOTE: if you just want to use the [synthetic data](https://github.com/CanDIG/katsu/tree/develop/chord_metadata_service/mohpackets/data/small_dataset/synthetic_data), you can skip this step.

```bash
export MOH_DATA_LOCATION=path/to/moh/data/
```

Run moh_ingest.py. This will represent severals options:

1. Run check: check if the you are ready to ingest the data.
2. Ingest data: import the data into katsu
3. Clean data: reset the database to the clean state. Use this if you want to start over. WARNING: be careful in production environment, as it irreversibe.

You can also run the script with the `-choice` to skip the menu and go straight to the choice you want.

```bash
python moh_ingest.py -choice 2
```
