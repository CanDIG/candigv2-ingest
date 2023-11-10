import argparse

import auth
import os
import re
import json
from ingest_result import IngestPermissionsException, IngestServerException, IngestUserException, IngestResult
import requests
from urllib.parse import urlparse


CANDIG_URL = os.getenv("CANDIG_URL", "")
HTSGET_URL = CANDIG_URL + "/genomics"
HOSTNAME = HTSGET_URL.replace(f"{urlparse(CANDIG_URL).scheme}://","")

def post_object(token, genomic_sample, clinical_samples, dataset, ref_genome="hg38", force=False):
    headers = {"Authorization": f"Bearer {token}"}
    print(f"working on {genomic_sample['id']}")
    url = f"{HTSGET_URL}/ga4gh/drs/v1/objects"

    # file object:
    access_method = {}
    if genomic_sample['file_access'].startswith("file://"):
        access_method["access_url"] = {
            "headers": [],
            "url": genomic_sample['file_access']
        }
        access_method["type"] = "file"

    else:
        access_method["access_id"] = genomic_sample['file_access']
        access_method["type"] = "s3"

    obj = {
        "access_methods": [
            access_method
        ],
        "id": genomic_sample["id"],
        "name": genomic_sample["id"],
        "description": "variant",
        "cohort": dataset,
        "version": "v1"
    }
    response = requests.post(url, json=obj, headers=headers)
    if response.status_code > 200:
        return response

    # index object:
    access_method = {}
    if genomic_sample['index_access'].startswith("file://"):
        access_method["access_url"] = {
            "headers": [],
            "url": genomic_sample['index_access']
        }
        access_method["type"] = "file"

    else:
        access_method["access_id"] = genomic_sample['index_access']
        access_method["type"] = "s3"

    obj = {
        "access_methods": [
            access_method
        ],
        "id": genomic_sample["index"],
        "name": genomic_sample["index"],
        "description": "index",
        "cohort": dataset,
        "version": "v1"
    }

    response = requests.post(url, json=obj, headers=headers)
    if response.status_code > 200:
        return response

    # add this genomic_id to the sample drs object, if available
    for sample in clinical_samples:
        genomic_contents = {"drs_uri": [f"{HOSTNAME}/{genomic_sample['id']}"],
                            "name": sample['sample_name_in_file'], "id": genomic_sample['id']}
        obj = {
            "id": f"{sample['sample_registration_id']}",
            "contents": [genomic_contents],
            "cohort": dataset,
            "description": "sample",
            "version": "v1"
        }

        response = requests.get(f"{url}/{'sample_registration_id'}", headers=headers)
        if response.status_code == 200:
            obj = response.json()
            obj['contents'].append(genomic_contents)

        response = requests.post(url, json=obj, headers=headers)
        if response.status_code != 200:
            return response

    # master object:
    obj = {
        "contents": [
            {
                "drs_uri": [
                    f"drs://{HOSTNAME}/{genomic_sample['id']}"
                ],
                "name": genomic_sample['id'],
                "id": genomic_sample["type"]
            },
            {
                "drs_uri": [
                    f"drs://{HOSTNAME}/{genomic_sample['index']}"
                ],
                "name": genomic_sample['index'],
                "id": "index"
            }
        ],
        "id": genomic_sample['id'],
        "name": genomic_sample['id'],
        "description": "wgs",
        "cohort": dataset,
        "version": "v1"
    }

    for sample in clinical_samples:
        clinical_obj = {"drs_uri": [f"{HOSTNAME}/{sample['sample_registration_id']}"],
                        "name": f"{sample['sample_registration_id']}",
                       "id": sample['sample_name_in_file'] }
        obj["contents"].append(clinical_obj)

    response = requests.post(url, json=obj, headers=headers)
    return response


def create_s3_sample(genomic_id: str, index: str, client):
    # If genomic_files is provided, it means the filenames do not correspond to the genomic_id names in the bucket
    # And have been provided manually.
    bucket_objects = [object.object_name for object in client['client'].list_objects(client["bucket"])]
    if (genomic_id not in bucket_objects) or ((genomic_id + '.' + index) not in bucket_objects):
        return IngestUserException("Genomic file or index specified not found in bucket: "
                                    f"{genomic_id} (index: {index})")
    if index == "tbi":
        type = 'variant'
    else:
        type = 'read'
    return {
            "id": genomic_id,
            "index": genomic_id + '.' + index,
            "type": type,
            "file_access": f"{client['endpoint']}/{client['bucket']}/{genomic_id}",
            "index_access": f"{client['endpoint']}/{client['bucket']}/{genomic_id}.{index}"
        }

def create_local_sample(genomic_id: str, index: str, path: str):
    if index == "tbi":
        type = 'variant'
    else:
        type = 'read'
    return {
            "id": genomic_id,
            "file": genomic_id,
            "index": genomic_id + '.' + index,
            "type": type,
            "file_access": f"file://{path}",
            "index_access": f"file://{path} + '.' + index"
        }

def htsget_ingest(token, dataset, sample, reference="hg38", indexing=False):
    local = False
    match = re.search("s3:\/\/(.+)\/(.+)", sample["access_method"])
    if match:
        endpoint = match.group(1)
        bucket = match.group(2)
    else:
        local = True
    if os.getenv("CANDIG_URL") == "":
        raise Exception("CANDIG_URL environment variable is not set")

    if not local:
        try:
            client = auth.get_minio_client(token, endpoint, bucket)
        except Exception as e:
            print(e)
            return IngestServerException("Failed to access S3 bucket %s. Did you add credentials to vault?" % bucket)
        # first, find all of the s3 objects related to this sample:
        object = create_s3_sample(sample["genomic_id"], sample["index"], client)
    else:
        object = create_local_sample(sample["genomic_id"], sample["index"], sample["access_method"].split("file://")[1])
    if isinstance(object, IngestResult):
        return object # An error occurred
    response = post_object(token, object, sample["samples"], dataset, ref_genome=reference, force=indexing)
    if (response.status_code > 200):
        print(response.text)
        if response.status_code < 500:
            return IngestUserException(response.text)
        else:
            return IngestServerException(response.text)
    return IngestResult(sample["genomic_id"])

def main():
    parser = argparse.ArgumentParser(description="A script that ingests a sample vcf and its index into htsget.")
    parser.add_argument("--samplefile", help="A file specifying a genomic sample")
    parser.add_argument("--dataset", help="dataset/cohort/program_id", required=True)
    parser.add_argument("--region", help="optional: s3 region", required=False) # Not used?
    parser.add_argument("--reference", help="optional: reference genome, either hg37 or hg38", required=False, default="hg38")
    parser.add_argument("--indexing", action="store_true", help="optional: force re-indexing", required=False)

    args = parser.parse_args()

    if args.samplefile:
        with open(args.samplefile) as f:
            genomic_sample = json.loads(f.read())

    result = htsget_ingest(auth.get_site_admin_token(), args.dataset, genomic_sample, args.reference,
                                    args.indexing)
    if result.value:
      print(result.value)

if __name__ == "__main__":
    main()