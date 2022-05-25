import argparse
import requests
import auth
import os
import json
from urllib.parse import urlparse

CANDIG_URL = os.getenv("CANDIG_URL", "")
HTSGET_URL = CANDIG_URL + "/genomics"
HOSTNAME = HTSGET_URL.replace(f"{urlparse(CANDIG_URL).scheme}://","")


def post_object(sample_id, file_dir, token):
    headers = {"Authorization": f"Bearer {token}"}
    obj = {
        "access_methods": [
            {
                "access_url": {
                    "url": f"file:///{file_dir}/{sample_id}.vcf.gz"
                },
                "type": "file"
            }
        ],
        "id": f"{sample_id}.vcf.gz",
        "name": f"{sample_id}.vcf.gz",
        "self_uri": f"drs://{HOSTNAME}/{sample_id}.vcf.gz",
        "version": "v1"
    }
    url = f"{HTSGET_URL}/ga4gh/drs/v1/objects"
    response = requests.post(url, json=obj, headers=headers)
    obj["access_methods"][0]["access_url"]["url"] += ".tbi"
    obj["id"] += ".tbi"
    obj["name"] += ".tbi"
    obj["self_uri"] += ".tbi"

    response = requests.post(url, json=obj, headers=headers)

    obj = {
        "contents": [
          {
            "drs_uri": [
              f"drs://localhost/{sample_id}.vcf.gz"
            ],
            "name": f"{sample_id}.vcf.gz",
            "id": "variant"
          },
          {
            "drs_uri": [
              f"drs://localhost/{sample_id}.vcf.gz.tbi"
            ],
            "name": f"{sample_id}.vcf.gz.tbi",
            "id": "index"
          }
        ],
        "id": sample_id,
        "name": sample_id,
        "self_uri": f"drs://{HOSTNAME}/{sample_id}",
        "version": "v1"
    }

    response = requests.post(url, json=obj, headers=headers)

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
    return response


def main():
    parser = argparse.ArgumentParser(description="A script that ingests a sample vcf and its index into htsget.")

    parser.add_argument("--sample", help="sample id", required=False)
    parser.add_argument("--samplefile", help="file with list of sample ids", required=False)
    parser.add_argument("--dir", help="file directory")
    parser.add_argument("--dataset", help="dataset name")

    args = parser.parse_args()

    samples = []
    if args.samplefile is not None:
        with open(args.samplefile) as f:
            lines = f.readlines()
            for line in lines:
                samples.append(line.strip())
    elif args.sample is not None:
        samples.append(args.sample)
    else:
        raise Exception("Either a sample name or a file of samples is required.")

    if CANDIG_URL == "":
        raise Exception("CANDIG_URL environment variable is not set")

    token = auth.get_site_admin_token()

    for sample in samples:
        post_object(sample, args.dir, token)
    post_to_dataset(samples, args.dataset, token)
    response = get_dataset_objects(args.dataset, token)
    print(json.dumps(response, indent=4))


if __name__ == "__main__":
    main()
