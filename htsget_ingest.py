import argparse
import requests
import auth
import os
import re
import json
from urllib.parse import urlparse

CANDIG_URL = os.getenv("CANDIG_URL", "")
HTSGET_URL = CANDIG_URL + "/genomics"
VAULT_URL = CANDIG_URL + "/vault"
HOSTNAME = CANDIG_URL.replace(f"{urlparse(CANDIG_URL).scheme}://","")

def collect_samples_for_genomic_id(genomic_id, client, prefix=""):
    # first, find all files that are related to this sample at the endpoint:
    files_iterator = client['client'].list_objects(client["bucket"], prefix=prefix+genomic_id)
    files = []
    for f in files_iterator:
        files.append(f.object_name)
    samples = []
    while len(files) > 0:
        f = files.pop(0)
        index_parse = re.match(r"(.+)\.(tbi|bai|crai|csi)", f)
        if index_parse is not None:
            # this is an index file, so it should have a corresponding file
            files.remove(index_parse.group(1))
            file = index_parse.group(1)
            # files.remove(f)
            index = f
            type = 'read'
            if index_parse.group(2) == 'tbi':
                type = 'variant'
            id_parse = re.match(r"(.+)\.(vcf|bam|cram|sam|bcf)(\.gz)*", file)
            samples.append(
                {
                    "id": id_parse.group(1),
                    "file": file,
                    "index": index,
                    "type": type
                }
            )
        else:
            files.append(f)
        if len(files) == 1: # hey, clearly this file doesn't have a buddy. This is wrong!
            print(f"Error: {name} doesn't have its matching index or file")
            break
    return samples


def post_objects(genomic_id, samples_to_create, client, token):
    endpoint = client["endpoint"]
    bucket = client["bucket"]
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{HTSGET_URL}/ga4gh/drs/v1/objects"

    for s in samples_to_create:
        # master object:
        obj = {
            "contents": [
              {
                "drs_uri": [
                  f"drs://{HOSTNAME}/{s['file']}"
                ],
                "name": s["file"],
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
            "self_uri": f"drs://{HOSTNAME}/{s['id']}",
            "version": "v1"
        }
        response = requests.post(url, json=obj, headers=headers)

        # file object:
        obj = {
            "access_methods": [
                {
                    "access_id": f"{endpoint}/{bucket}/{s['file']}",
                    "type": "s3"
                }
            ],
            "id": s['file'],
            "name": s['file'],
            "self_uri": f"drs://{HOSTNAME}/{s['file']}",
            "version": "v1"
        }
        response = requests.post(url, json=obj, headers=headers)

        # index object:
        obj = {
            "access_methods": [
                {
                    "access_id": f"{endpoint}/{bucket}/{s['index']}",
                    "type": "s3"
                }
            ],
            "id": s['index'],
            "name": s['index'],
            "self_uri": f"drs://{HOSTNAME}/{s['index']}",
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
    return response.json()


def add_aws_credential(client, token):
    # get client token for site_admin:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "charset": "utf-8"
    }
    body = {
        "jwt": token,
        "role": "site_admin"
    }
    url = f"{VAULT_URL}/v1/auth/jwt/login"
    response = requests.post(url, json=body, headers=headers)
    if response.status_code == 200:
        client_token = response.json()["auth"]["client_token"]
        headers["X-Vault-Token"] = client_token
    
    # check to see if credential exists:
    url = f"{VAULT_URL}/v1/aws/{client['endpoint']}-{client['bucket']}"
    response = requests.get(url, headers=headers)
    if response.status_code == 404:
        # add credential:
        body = {
            "access": client['access'],
            "secret": client['secret']
        }
        response = requests.post(url, headers=headers, json=body)
    if response.status_code >= 200 and response.status_code < 300:
        return True, None
    return False, json.dumps(response.json())


def main():
    parser = argparse.ArgumentParser(description="A script that ingests a sample vcf and its index into htsget.")

    parser.add_argument("--sample", help="sample id", required=False)
    parser.add_argument("--samplefile", help="file with list of sample ids", required=False)
    parser.add_argument("--endpoint", help="s3 endpoint")
    parser.add_argument("--bucket", help="s3 bucket name")
    parser.add_argument("--dataset", help="dataset name")
    parser.add_argument("--awsfile", help="s3 credentials")
    parser.add_argument("--region", help="optional: s3 region", required=False)
    parser.add_argument("--prefix", help="optional: s3 prefix", required=False, default="")

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
    
    # parse the awsfile:
    result = auth.parse_aws_credential(args.awsfile)
    if "error" in result:
        raise Exception(f"Failed to parse awsfile: {result['error']}")

    client = auth.get_minio_client(args.endpoint, args.bucket, access_key=result["access"], secret_key=result["secret"], region=args.region)
    success, reason = add_aws_credential(client, token)
    if not success:
        raise Exception(f"Failed to add AWS credential to vault: {reason}")
    for sample in samples:
        # first, find all of the s3 objects related to this sample:
        objects_to_create = collect_samples_for_genomic_id(sample, client, prefix=args.prefix)
        print(objects_to_create)
        post_objects(sample, objects_to_create, client, token)
    post_to_dataset(samples, args.dataset, token)
    response = get_dataset_objects(args.dataset, token)
    print(json.dumps(response, indent=4))


if __name__ == "__main__":
    main()
