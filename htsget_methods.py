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

def post_to_dataset(sample_ids, dataset, token):
    headers = {"Authorization": f"Bearer {token}"}
    drsobjects = map(lambda s : f"drs://{HOSTNAME}/{s}", sample_ids)
    obj = {
        "id": dataset,
        "drsobjects": list(drsobjects)
    }
    print(obj)
    url = f"{HTSGET_URL}/ga4gh/drs/v1/datasets"
    request = requests.Request(method="POST", url=url, json=obj, headers=headers)
    if not auth.is_authed(request):
        return IngestPermissionsException(dataset)
    response = requests.Session().send(request.prepare())
    return response


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


def post_objects(genomic_id, genomic_objs_to_create, token, clinical_id=None, ref_genome="hg38", force=False):
    headers = {"Authorization": f"Bearer {token}"}

    for s in genomic_objs_to_create:
        print(f"working on {s['id']}")
        url = f"{HTSGET_URL}/ga4gh/drs/v1/objects"
        # master object:
        obj = {
            "contents": [
              {
                "drs_uri": [
                  f"drs://{HOSTNAME}/{s['file']}"
                ],
                "name": s['file'],
                "id": s["type"]
              },
              {
                "drs_uri": [
                  f"drs://{HOSTNAME}/{s['index']}"
                ],
                "name": s['index'],
                "id": "index"
              }
            ],
            "id": s['id'],
            "name": s['id'],
            "version": "v1"
        }
        response = requests.post(url, json=obj, headers=headers)
        if response.status_code > 200:
            return response
        genomic_drs_obj = response.json()['self_uri']

        # file object:
        access_method = {}
        if s['file_access'].startswith("file://"):
            access_method["access_url"] = {
                "headers": [],
                "url": s['file_access']
            }
            access_method["type"] = "file"

        else:
            access_method["access_id"] = s['file_access']
            access_method["type"] = "s3"

        obj = {
            "access_methods": [
                access_method
            ],
            "id": s["file"],
            "name": s["file"],
            "version": "v1"
        }
        response = requests.post(url, json=obj, headers=headers)
        if response.status_code > 200:
            return response

        # index object:
        access_method = {}
        if s['index_access'].startswith("file://"):
            access_method["access_url"] = {
                "headers": [],
                "url": s['index_access']
            }
            access_method["type"] = "file"

        else:
            access_method["access_id"] = s['index_access']
            access_method["type"] = "s3"

        obj = {
            "access_methods": [
                access_method
            ],
            "id": s["index"],
            "name": s["index"],
            "version": "v1"
        }
        response = requests.post(url, json=obj, headers=headers)
        if response.status_code > 200:
            return response

        # add this genomic_id to the sample drs object, if available
        genomic_content = {
            "drs_uri": [
                genomic_drs_obj
            ],
            "name": genomic_id,
            "id": "genomic"
        }

        obj = {
            "id": clinical_id,
            "contents": [genomic_content],
            "version": "v1"
        }

        response = requests.get(f"{url}/{clinical_id}", headers=headers)
        if response.status_code == 200:
            obj = response.json()
            obj['contents'].append(genomic_content)

        requests.post(url, json=obj, headers=headers)

        # index for search:
        url = f"{HTSGET_URL}/htsget/v1/variants/{s['id']}/index"
        response = requests.get(url, params={"genome": ref_genome, "force": force, "genomic_id": genomic_id}, headers=headers)
        return response
