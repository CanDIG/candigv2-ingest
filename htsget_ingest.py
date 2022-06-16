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


def post_object(sample_id, endpoint, bucket, token):
    headers = {"Authorization": f"Bearer {token}"}
    obj = {
        "access_methods": [
            {
                "access_id": f"{endpoint}/{bucket}/{sample_id}.vcf.gz",
                "type": "s3"
            }
        ],
        "id": f"{sample_id}.vcf.gz",
        "name": f"{sample_id}.vcf.gz",
        "self_uri": f"drs://{HOSTNAME}/{sample_id}.vcf.gz",
        "version": "v1"
    }
    url = f"{HTSGET_URL}/ga4gh/drs/v1/objects"
    response = requests.post(url, json=obj, headers=headers)
    obj["access_methods"][0]["access_id"] += ".tbi"
    obj["id"] += ".tbi"
    obj["name"] += ".tbi"
    obj["self_uri"] += ".tbi"

    response = requests.post(url, json=obj, headers=headers)

    obj = {
        "contents": [
          {
            "drs_uri": [
              f"drs://{HOSTNAME}/{sample_id}.vcf.gz"
            ],
            "name": f"{sample_id}.vcf.gz",
            "id": "variant"
          },
          {
            "drs_uri": [
              f"drs://{HOSTNAME}/{sample_id}.vcf.gz.tbi"
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
            print(obj)
            url = f"{HTSGET_URL}/ga4gh/drs/v1/objects{urlparse(obj).path}"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                objects.append(response.json())
                if "contents" in response.json():
                    for item in response.json()["contents"]:
                        drs_objs.insert(0, item["drs_uri"][0])
        return objects
    return response


def add_aws_credential(endpoint, bucket, awsfile, token):
    # eat any http stuff from endpoint:
    endpoint_parse = re.match(r"https*:\/\/(.+)?", endpoint)
    if endpoint_parse is not None:
        endpoint = endpoint_parse.group(1)
        
    # if it's any sort of amazon endpoint, it can just be s3.amazonaws.com
    if "amazonaws.com" in endpoint:
        endpoint = "s3.amazonaws.com"
    print(endpoint)
    # parse the awsfile:
    access = None
    secret = None
    with open(awsfile) as f:
        lines = f.readlines()
        while len(lines) > 0 and (access is None or secret is None):
            line = lines.pop(0)
            print(len(lines))
            parse_access = re.match(r"(aws_access_key_id|AWSAccessKeyId)\s*=\s*(.+)$", line)
            if parse_access is not None:
                access = parse_access.group(2)
            parse_secret = re.match(r"(aws_secret_access_key|AWSSecretKey)\s*=\s*(.+)$", line)
            if parse_secret is not None:
                secret = parse_secret.group(2)
    if access is None:
        return False, "awsfile did not contain access ID"
    if secret is None:
        return False, "awsfile did not contain secret key"

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
    url = f"{VAULT_URL}/v1/aws/{endpoint}-{bucket}"
    response = requests.get(url, headers=headers)
    print(response.status_code)
    if response.status_code == 404:
        # add credential:
        body = {
            "access": access,
            "secret": secret
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
    endpoint = args.endpoint
    
    # eat any http stuff from endpoint:
    endpoint_parse = re.match(r"https*:\/\/(.+)?", endpoint)
    if endpoint_parse is not None:
        endpoint = endpoint_parse.group(1)
        
    # if it's any sort of amazon endpoint, it can just be s3.amazonaws.com
    if "amazonaws.com" in endpoint:
        endpoint = "s3.amazonaws.com"
    print(endpoint)

    
    success, reason = add_aws_credential(endpoint, args.bucket, args.awsfile, token)
    if not success:
        raise Exception(f"Failed to add AWS credential to vault: {reason}")
    for sample in samples:
        post_object(sample, endpoint, args.bucket, token)
    post_to_dataset(samples, args.dataset, token)
    response = get_dataset_objects(args.dataset, token)
    print(json.dumps(response, indent=4))


if __name__ == "__main__":
    main()
