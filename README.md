# candigv2-ingest

Ingest data into the [CanDIGv2 stack](https://github.com/CanDIG/CanDIGv2). This repository assumes that you have a functional instance of the [CanDIGv2 software stack](https://github.com/CanDIG/CanDIGv2).

This repository can either be run standalone or as a Docker container.

## What you'll need

* A valid user for CanDIGv2 that has site administration credentials.
* List of users that will have access to this dataset.
* Clinical data, saved as either an Excel file or as a set of csv files.
* Genomic data files in vcf, bam or cram format with paired index files for each.
* File map of genomic files in a csv file, linking genomic sample IDs to the clinical samples.
* (if needed) Credentials for s3 endpoints: url, access ID, secret key.
* Reference genome used for the variant files.
* Manifest and mappings for [`clinical_ETL_code`](https://github.com/CanDIG/clinical_ETL_code) conversion.

## Setup
Using a Python 3.10+ environment, run the following:

```bash
pip install -r requirements.txt
```

### Set environment variables

* CANDIG_URL (same as TYK_LOGIN_TARGET_URL, if you're using CanDIGv2's example.env)
* KEYCLOAK_PUBLIC_URL
* CANDIG_CLIENT_ID
* CANDIG_CLIENT_SECRET
* CANDIG_SITE_ADMIN_USER
* CANDIG_SITE_ADMIN_PASSWORD

For convenience, you can generate a file `env.sh` from your [`CanDIGv2`](https://github.com/CanDIG/CanDIGv2) repo:

```bash
cd CanDIGv2
python settings.py
source env.sh
```

## How to use candigv2-ingest

`candigv2-ingest` can be used as either a command-line tool, a local API server or a docker container. To run the command line scripts, set your environment variables and follow the command line instructions in the sections below. To use the local API, set your environment variables, run `python app.py`, and follow the API instructions in the sections below. The API will be available at `localhost:1236`. A swagger UI is also available at `/ui`. Docker instructions can be found at the [bottom of this document](#Run-as-Docker-Container). To authorize yourself for these endpoints, you will need to set the Authorization header to a keycloak bearer token (in the format `"Bearer ..."` without the quotes).

## 1. Clinical data

### i. Prepare clinical data

Before being ingested, data must be transformed to the CanDIG MoH data model. This can be done using CanDIG's [`clinical_ETL_code`](https://github.com/CanDIG/clinical_ETL_code) repository. Please visit that repository for full instructions and return to ingest when you have a valid JSON file with a set of donors. An example file can be found at [tests/single_ingest.json](tests/single_ingest.json)

### ii. Ingest clinical data

The preferred method for clinical data ingest is using the API.

#### API

The clinical ingest API runs at `/ingest/clinical`. Simply send a request with an authorized bearer token and a JSON body with your `DonorWithClinicalData` object. See the swagger UI/[schema](ingest_openapi.yaml) for the response format.

#### Command line

This method is mainly used for development work but may also be used if the JSON body is too big to send easily via POST.

To ingest via the commandline script, the location of your clinical data JSON must be specified. This can be done either by:

supplying it as an argument to the script:

```commandline
python katsu_ingest.py --input path/to/clinical/data/
```

Or by exporting an environment variable `CLINICAL_DATA_LOCATION`, then running the script:

```bash
export CLINICAL_DATA_LOCATION=path/to/clinical/data/
source env.sh
python katsu_ingest.py
```

## 2. Genomic data

**First**, ensure that the relevant clinical data is ingested, as this must be completed before your genomic data is ingested.

### i. Prepare Genomic files

Accepted file types:
* Variants in VCF (`.vcf` or `.vcf.gz`) with paired tabix (`.tbi`) files
* Aligned reads (`.bam` or `.cram`) with paired index files (`.bai`, `.crai`)

For each file, you need to have a note of:
* The `submitter_sample_id` that the file should link to
* How that sample is referred to within the file, e.g. the `sample ID` in a VCF or `@RG SM` in BAM/CRAM
* Where the file is located in relation to the running htsget server

This information will be used to create the genomic ingest JSON file required for ingest

> [!CAUTION]
> It is important to ensure no donor identifiable information is contained within the genomic files, such as in BAM/CRAM headers or VCF metadata

### ii. Move files to an accessible location

Files must be visible to the running htsget server and can either be made available via S3 compatible storage or by storing the files locally within the htsget container or via a NFS mount.

#### S3-compatible system

<blockquote><details><summary>How do I move files into an S3-type bucket?</summary>
Ingest files into S3-compatible stores one endpoint/bucket at a time.

```bash
python s3_ingest.py --sample <sample>|--samplefile <samplefile> --endpoint <S3 endpoint> --bucket <S3 bucket> --awsfile <aws credentials>
```

</details></blockquote>


##### Add S3 credentials to vault
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

#### Local or mounted storage to htsget

If necessary, genomic samples can be loaded directly from the htsget container's internal storage. Simply `docker cp` the sample files somewhere into the container and prefix your access_method with `file:///` instead of `s3://` (see below).

### iii. Prepare the Genomic JSON file

Metadata about each genomic file should be specified in a `JSON` file.

The file should contain an array of dictionaries, where each item represents a single file. Each dictionary specifies important information about the genomic file and how it links to the ingested clinical data. The structure of this dictionary is specified in the ingest [openapi schema](ingest_openapi.yaml#L171C8-L171C8), an [example file](tests/genomic_ingest.json) exists within the test files and a commented example is below:

```
[
    {   ## Example linking to genomic and index files in s3 storage to a single sample
        "program_id": "SYNTHETIC-2",      # The name of the program
        "genomic_file_id": "HG00096.cnv",  # The identifier used to identify the genomic file, usually the filename, minus extensions
        "main": {                         # location and name of the main genomic file, bam/cram/vcf
            "access_method": "s3://s3.us-east-1.amazonaws.com/1000genomes/release/20130502/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz?public=true",
            "name": "HG00096.cnv.vcf.gz"
        },
        "index": {                        # location and name of the index for the main genomic file, bai/crai/
            "access_method": "s3://s3.us-east-1.amazonaws.com/1000genomes/release/20130502/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz?public=true",
            "name": "HG00096.cnv.vcf.gz.tbi"
        },
        "metadata": {                     # Metadata about the file
            "sequence_type": "wgs",       # type of data sequenced (whole genome or whole transcriptome), allowed values: [wgs, wts]
            "data_type": "variant",       # type of data represented, allowed values: [variant, read]
            "reference": "hg37"           # which reference genome was used for alignment, allowed values: [hg37, hg38]
        },
        "samples": [                      # Linkage to one or more samples that the genomic file was derived from
            {
                "genomic_file_sample_id": "HG00096",  # The name of the sample in the genomic file
                "submitter_sample_id": "SAMPLE_REGISTRATION_1"   # The submitter_sample_id to link to
            }
        ]
    },
    {  ## Example linking genomic and index files in local storage to multiple samples
        "program_id": "SYNTHETIC-2",
        "genomic_file_id": "multisample",
        "main": {
            "access_method": "file:////app/htsget_server/data/files/multisample_1.vcf.gz",
            "name": "multisample_1.vcf.gz"
        },
        "index": {
            "access_method": "file:////app/htsget_server/data/files/multisample_1.vcf.gz.tbi",
            "name": "multisample_1.vcf.gz.tbi"
        },
        "metadata": {
            "sequence_type": "wgs",
            "data_type": "variant",
            "reference": "hg37"
        },
        "samples": [
            {
                "genomic_file_sample_id": "TUMOR",
                "submitter_sample_id": "SAMPLE_REGISTRATION_4"
            },
            {
		"genomic_file_sample_id": "NORMAL",
		"submitter_sample_id": "SPECIMEN_5"
	    }
        ]
    }
]
```

> [!Tip]
> - `genomic_file_id` is the filename of the variation file (e.g. HG00096.vcf.gz, HG00096.bam)
> - Access methods can either be of the format `s3://[endpoint]/[bucket name]` or `file:///[directory relative to root on htsget container]`.
> - `submitter_sample_id`(s) are the (mandatory) links to the `Sample Registration objects uploaded during clinical data ingest.
> - `index` is the file location and name of the index file; for instance a tabix (`tbi`) or cram index (`crai`)
> - If an S3 bucket access method is provided, assuming you have properly added the S3 credentials to vault [(see above)](#Add-s3-credentials-to-vault), the service will scan the S3 bucket to ensure the relevant files are present.
> - There is no validation that the genomic files exist locally or are mounted to htsget. If the local (`file:///`) method is used it is important to check all files are present before proceeding with ingest.

### iv. Ingest genomic files

#### API
Use the `/ingest/genomic` endpoint with the proper Authorization headers and your genomic JSON as specified above for the body to ingest and link to the clinical dataset program_id.

#### Command line

To ingest using an S3 container, once the files have been added, you can run the htsget_ingest.py script:

```bash
python htsget_ingest.py --samplefile [JSON-formatted sample data as specified above]
```

## 3. Adding authorization for users to programs
A site administrator can use either the `opa_ingest.py` command-line script or the API to add authorization for a user to access a program.

#### API
Use the `/ingest/program/{program_id}/email/{email}` to add or remove a user's email address to the list of users authorized to access that program. Authorization headers for a site admin user must be provided. A POST request adds authorization, while a DELETE request revokes it.

#### Command line

```bash
python opa_ingest.py --user|userfile [either a user email or a file of user emails] -- dataset [name of dataset] [--remove]
```

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

<!--- ## Authorizing users for the new dataset

> [!WARNING]
> OPA ingest is currently not functional, so these instructions will not work.
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
--->
