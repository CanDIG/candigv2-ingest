import requests
import auth
import os
import re
from urllib.parse import urlparse

from ingest_result import IngestPermissionsException

CANDIG_URL = os.getenv("CANDIG_URL", "")
HTSGET_URL = CANDIG_URL + "/genomics"
VAULT_URL = CANDIG_URL + "/vault"
HOSTNAME = HTSGET_URL.replace(f"{urlparse(CANDIG_URL).scheme}://","")

def get_dataset_objects(dataset, token):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{HTSGET_URL}/ga4gh/drs/v1/datasets/{dataset}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        objects = []
        drs_objs = response.json()["drsobjects"]
        while len(drs_objs) > 0:
            obj = drs_objs.pop(0)
            drs_obj_match = re.match(r"^(.+)\/(.+)$", obj)
            url = f'{HTSGET_URL}/ga4gh/drs/v1/objects/{drs_obj_match.group(2)}'
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                objects.append(response.json())
                if "contents" in response.json():
                    for item in response.json()["contents"]:
                        drs_objs.insert(0, item["drs_uri"][0])
        return objects
    return response.json()


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