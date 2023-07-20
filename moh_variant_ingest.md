For the MoH data model, we will get vcf files that represent paired samples of tumour/normal calls.

We need to know where the vcf file and its index file are located. The genomic_id will be the base filename of the vcf file, without the vcf.gz extension.

If these are located in an S3 bucket, we need to know:
    - endpoint
    - bucket
    - object_id
    - access_key
    - secret_key
If these are located as a file mount on the htsget container, we need to know:
    - the local file path

We also need to know what sample_registrations represent the tumour and normal sequences in the file.

```
{
    "program_id": program_id,
    "genomic_id": base_filename,
    "access_method": {
        anyOf: [
            "s3://endpoint/bucket",
            "file:///local_file_path"
        ]
    },
    "samples": [
        {
            "sample_registration_id": sample_registration_id_1,
            "sample_name_in_file": "TUMOUR"
        },
        {
            "sample_registration_id": sample_registration_id_2,
            "sample_name_in_file": "NORMAL"
        }
    ]
}
```
The ingest program should take this file as input.
Adding the S3 credentials to Vault should happen in a separate step.

The final shape of the DrsObjects that represent this:
```
[
    {
        "id": f"{input['genomic_id']}".vcf.gz.tbi,
        "mime_type": "application/octet-stream",
        "name": f"{input['genomic_id']}".vcf.gz.tbi,
        "contents": [
            {
                "type": "s3",
                "access_id": f"{input['access_method']}/{input['genomic_id']}".vcf.gz.tbi"
            }
        ],
        "version": "v1"
    },
    {
        "id": f"{input['genomic_id']}".vcf.gz,
        "mime_type": "application/octet-stream",
        "name": f"{input['genomic_id']}".vcf.gz,
        "contents": [
            {
                "type": "s3",
                "access_id": f"{input['access_method']}/{input['genomic_id']}".vcf.gz"
            }
        ],
        "version": "v1"
    },
    {
        "id": f"{input['program_id']}_{input['sample'][0]['sample_registration_id']},
        "contents": [
            {
                "drs_uri": [
                    f"{drs_url}/f"{input['genomic_id']}""
                ],
                "name": input['sample'][0]['sample_name_in_file'],
                "id": f"{input['genomic_id']}"
            }
        ],
        "version": "v1"
    },
    {
        "id": f"{input['program_id']}_{input['sample'][1]['sample_registration_id']},
        "contents": [
            {
                "drs_uri": [
                    f"{drs_url}/f"{input['genomic_id']}""
                ],
                "name": input['sample'][1]['sample_name_in_file'],
                "id": f"{input['genomic_id']}"
            }
        ],
        "version": "v1"
    },
    {
        "id": f"{input['genomic_id']}",
        "mime_type": "application/octet-stream",
        "name": f"{input['genomic_id']}",
        "contents": [
            {
                "drs_uri": [
                    f"{drs_url}/f"{input['genomic_id']}".vcf.gz.tbi"
                ],
                "name": f"{input['genomic_id']}".vcf.gz.tbi,
                "id": "index"
            },
            {
                "drs_uri": [
                    f"{drs_url}/f"{input['genomic_id']}".vcf.gz"
                ],
                "name": f"{input['genomic_id']}".vcf.gz,
                "id": "variant"
            },
            {
                "drs_uri": [
                    f"{drs_url}/{input['program_id']}_{input['sample'][0]['sample_registration_id']}"
                ],
                "name": {input['program_id']}_{input['sample'][0]['sample_registration_id']},
                "id": f"{input['sample'][0]['sample_name_in_file']}"
            },
            {
                "drs_uri": [
                    f"{drs_url}/{input['program_id']}_{input['sample'][1]['sample_registration_id']}"
                ],
                "name": {input['program_id']}_{input['sample'][1]['sample_registration_id']},
                "id": f"{input['sample'][1]['sample_name_in_file']}"
            }
        ],
        "version": "v1"
    }
]
```

These objects can be POSTed to /ga4gh/drs/v1/objects.