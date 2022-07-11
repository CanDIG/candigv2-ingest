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

For convenience, you can update these in env.sh and run `source env.sh`.

## Authorizing users for the new dataset
Create a new access.json file:
```bash
python opa_ingest.py --dataset <dataset> --userfile <user file> > access.json
```

Alternately, you can add a single user:
```bash
python opa_ingest.py --dataset <dataset> --user <username> > access.json
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

Ingest files into S3-compatible stores one endpoint/bucket at a time.

```bash
python s3_ingest.py --sample <sample>|--samplefile <samplefile> --endpoint <S3 endpoint> --bucket <S3 bucket> --awsfile <aws credentials>
```

### Ingest into Htsget
To make the genomic files accessible to the htsget server, run:

```bash
python htsget_ingest.py --sample <sample>|--samplefile <samplefile> --dataset <dataset> --endpoint <S3 endpoint> --bucket <S3 bucket> --awsfile <aws credentials>
```

### Ingest into candig-server
Candig-server performs variant search for CanDIG. It needs its data ingested from the local command line; there is no REST API for ingest.

* You'll need to know the name of the referenceset on your candig-server instance. Make sure that the referenceset needed for your variant files is already created on your candig-server instance.

<blockquote><details><summary>How do I add a referenceset?</summary>
See https://candig-server.readthedocs.io/en/v1.6.0/datarepo.html#add-referenceset for detailed instructions, but a quick version:

From inside the candig-server instance, download the reference files:
```bash
curl https://daisietestbucket1.s3.amazonaws.com/hs37d5.fa.gz > /hs37d5.fa.gz
curl https://daisietestbucket1.s3.amazonaws.com/hs37d5.fa.gz.gzi > /hs37d5.fa.gz.gzi
```
Then add the reference set:
```bash
candig_repo add-referenceset <your db> /hs37d5.fa.gz \
		--description "NCBI37 assembly of the human genome" \
		--species '{"termId": "NCBI:9606", "term": "Homo sapiens"}' \
		--name hs37d5 \
		--sourceUri http://ftp.1000genomes.ebi.ac.uk/vol1/ftp/technical/reference/phase2_reference_assembly_sequence/hs37d5.fa.gz
```
</details></blockquote>

* You'll need a csv input file containing the mapping between the patient_ids and the variant_ids and the names of the columns corresponding to each. 
* The variant files need to be mounted on a path that is accessible to candig-server.

Run the candig_server_ingest.py script to generate a shell script and input json that you can copy and run on your candig-server instance.
```bash
python candig_server_ingest.py --dataset DATASET --input_file INPUT_FILE --patient_id PATIENT_ID_COL_NAME --variant_file_id VARIANT_ID_COL_NAME --path FILE_PATH --reference REFSET_NAME
```

This command will generate two files in a temp directory, `candigv1_data.json` and `candigv1_ingest.sh`. Copy these onto the candig_server instance and run `bash candigv1_ingest.sh`.

If you're running candig-server in the CanDIGv2 Docker stack:
```bash
docker cp temp/candigv1_data.json candigv2_candig-server_1:/app/candig-server/
docker cp temp/candigv1_ingest.sh candigv2_candig-server_1:/app/candig-server/
docker exec candigv2_candig-server_1 /app/candig-server/candigv1_ingest.sh
``` 

Don't forget that you need to restart the candig-server instance to pick up the changes!

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
    if genomic_id is None:
        return None
    return {"genomic_id": genomic_id}
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
