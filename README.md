# candigv2-ingest
Ingest data into the CanDIGv2 stack

This repository assumes that you have installed CanDIGv2 already. 
<!-- Set the environment variable CANDIG_HOME to the location of that CanDIGv2 directory. -->
Set the env var CHORD_METADATA_INGEST_URL to the direct ingest url for your Katsu instance.

## Types of data
* Clinical data, saved as either an Excel file or as a set of csv files.
* Genomic data files in vcf format.
* File map of genomic files in a csv file, linking vcf files to the clinical samples.
* Manifest and mappings for clinical_ETL conversion.

Use clinical_etl to generate an input json file.
Create a barebones ingest file for candig-server (should only need file map)


ingest into:
* candig-server: patientID, sampleID, vcf file for variant search
* katsu: clinical data and link to htsget
* htsget: ingest DRS object
* opa: set up permissions for dataset


Run `make all` to install a synthetic project called `mohccn` and a dataset called `mcode-synthetic`.
Opa will allow the user specified in `$CANDIG_HOME/tmp/secrets/keycloak-test-user` to access the dataset.

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
