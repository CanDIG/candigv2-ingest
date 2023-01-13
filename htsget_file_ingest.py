import argparse
import requests
import auth
import os
import re
import json
from urllib.parse import urlparse
import time

CANDIG_URL = os.getenv("CANDIG_URL", "")
HTSGET_URL = CANDIG_URL + "/genomics"
VAULT_URL = CANDIG_URL + "/vault"
HOSTNAME = CANDIG_URL.replace(f"{urlparse(CANDIG_URL).scheme}://","")

def collect_samples_for_genomic_id(genomic_id, file):
    type_parse = re.match(r"(.+)\.(vcf|bam|cram|sam|bcf)(\.gz)*", file)
    if type_parse is not None:
        if type_parse.group(2) == 'vcf' or type_parse.group(2) == 'bcf':
            type = 'variant'
            index = f"{file}.tbi"
        elif type_parse.group(2) == 'bam' or type_parse.group(2) == 'sam':
            type = 'read'
            index = f"{file}.bai"
        elif type_parse.group(2) == 'cram':
            type = 'read'
            index = f"{file}.crai"
        return {
                "id": genomic_id,
                "file": file,
                "index": index,
                "type": type
            }


def post_objects(genomic_id, samples_to_create, token, ref_genome="hg38", force=False):
    headers = {"Authorization": f"Bearer {token}"}

    for s in samples_to_create:
        filename = os.path.basename(s['file'])
        filepath = os.path.abspath(s['file'])
        indexname = os.path.basename(s['index'])
        indexpath = os.path.abspath(s['index'])
        print(f"working on {s['id']}")
        url = f"{HTSGET_URL}/ga4gh/drs/v1/objects"
        # master object:
        obj = {
            "contents": [
              {
                "drs_uri": [
                  f"drs://{HOSTNAME}/{filename}"
                ],
                "name": filename,
                "id": s["type"]
              },
              {
                "drs_uri": [
                  f"drs://{HOSTNAME}/{indexname}"
                ],
                "name": indexname,
                "id": "index"
              }
            ],
            "id": s['id'],
            "name": s['id'],
            "self_uri": f"drs://{HOSTNAME}/{s['id']}",
            "version": "v1"
        }
        response = requests.post(url, json=obj, headers=headers)
        if response.status_code > 200:
            print(response.text)

        # file object:
        obj = {
            "access_methods": [
                {
                    "access_url": {
                        "headers": [],
                        "url": f"file://{filepath}"
                    },
                    "type": "file"
                }
            ],
            "id": filename,
            "name": filename,
            "self_uri": f"drs://{HOSTNAME}/{filename}",
            "version": "v1"
        }
        response = requests.post(url, json=obj, headers=headers)
        if response.status_code > 200:
            print(response.text)

        # index object:
        obj = {
            "access_methods": [
                {
                    "access_url": {
                        "headers": [],
                        "url": f"file://{indexpath}"
                    },
                    "type": "file"
                }
            ],
            "id": indexname,
            "name": indexname,
            "self_uri": f"drs://{HOSTNAME}/{indexname}",
            "version": "v1"
        }
        response = requests.post(url, json=obj, headers=headers)
        if response.status_code > 200:
            print(response.text)
        
        # index for search:
        url = f"{HTSGET_URL}/htsget/v1/variants/{s['id']}/index"
        response = requests.get(url, params={"genome": ref_genome, "force": force, "genomic_id": genomic_id}, headers=headers)
        if response.status_code > 200:
            print(response.text)
    return response


def post_to_dataset(sample_ids, dataset, token):
    headers = {"Authorization": f"Bearer {token}"}
    drsobjects = map(lambda s : f"drs://{HOSTNAME}/{s}", sample_ids)
    obj = {
        "id": dataset,
        "drsobjects": list(drsobjects)
    }
    url = f"{HTSGET_URL}/ga4gh/drs/v1/datasets"
    response = requests.post(url, json=obj, headers=headers)


def get_dataset_objects(dataset, token):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{HTSGET_URL}/ga4gh/drs/v1/datasets/{dataset}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        objects = []
        drs_objs = response.json()["drsobjects"]
        while len(drs_objs) > 0:
            obj = drs_objs.pop(0)
            url = f"{HTSGET_URL}/ga4gh/drs/v1/objects{urlparse(obj).path}"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                objects.append(response.json())
                if "contents" in response.json():
                    for item in response.json()["contents"]:
                        drs_objs.insert(0, item["drs_uri"][0])
        return objects
    return response.json()


def main():
    parser = argparse.ArgumentParser(description="A script that ingests a sample vcf and its index into htsget.")

    parser.add_argument("--sample", help="genomic sample id")
    parser.add_argument("--file", help="path to main file")
    parser.add_argument("--dataset", help="dataset name")
    parser.add_argument("--reference", help="optional: reference genome, either hg37 or hg38", required=False, default="hg38")
    parser.add_argument('--indexing', action="store_true", help="optional: force re-indexing")

    args = parser.parse_args()

    if CANDIG_URL == "":
        raise Exception("CANDIG_URL environment variable is not set")

    token = auth.get_site_admin_token()
    
    token = auth.get_site_admin_token()
    objects_to_create = collect_samples_for_genomic_id(args.sample, args.file)
    post_objects(args.sample, [objects_to_create], token, ref_genome=args.reference, force=args.indexing)
    post_to_dataset([args.sample], args.dataset, token)
    response = get_dataset_objects(args.dataset, token)
    print(json.dumps(response, indent=4))


if __name__ == "__main__":
    main()
