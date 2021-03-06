import os
import re
import requests
from minio import Minio


def get_site_admin_token():
    payload = {
        "client_id": os.environ.get("CANDIG_CLIENT_ID"),
        "client_secret": os.environ.get("CANDIG_CLIENT_SECRET"),
        "grant_type": "password",
        "username": os.environ.get("CANDIG_SITE_ADMIN_USER"),
        "password": os.environ.get("CANDIG_SITE_ADMIN_PASSWORD"),
        "scope": "openid"
    }
    response = requests.post(f"{os.environ.get('KEYCLOAK_PUBLIC_URL')}/auth/realms/candig/protocol/openid-connect/token", data=payload)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception("Check for environment variables")
    


def get_minio_client(s3_endpoint, bucket, access_key=None, secret_key=None, region=None):
    # eat any http stuff from endpoint:
    endpoint_parse = re.match(r"https*:\/\/(.+)?", s3_endpoint)
    if endpoint_parse is not None:
        endpoint = endpoint_parse.group(1)
        
    # if it's any sort of amazon endpoint, it can just be s3.amazonaws.com
    if "amazonaws.com" in s3_endpoint:
        endpoint = "s3.amazonaws.com"
    else:
        endpoint = s3_endpoint
    if bucket is None:
        bucket = "candigtest"
    if s3_endpoint is not None:
        endpoint = s3_endpoint
        if access_key is None or secret_key is None:
            raise Exception(f"AWS credentials were not provided")
    else:
        endpoint = "play.min.io:9000"
        access_key="Q3AM3UQ867SPQQA43P2F"
        secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG"
    if region is None:
        client = Minio(
            endpoint = endpoint,
            access_key = access_key,
            secret_key = secret_key
        )
    else:
        client = Minio(
            endpoint = endpoint,
            access_key = access_key,
            secret_key = secret_key,
            region = region
        )

    if not client.bucket_exists(bucket):
        if 'region' is None:
            client.make_bucket(bucket)
        else:
            client.make_bucket(bucket, location=region)

    return {
        "endpoint": endpoint,
        "client": client, 
        "bucket": bucket,
        "access": access_key,
        "secret": secret_key
    }


def parse_aws_credential(awsfile):
    # parse the awsfile:
    access = None
    secret = None
    with open(awsfile) as f:
        lines = f.readlines()
        while len(lines) > 0 and (access is None or secret is None):
            line = lines.pop(0)
            parse_access = re.match(r"(aws_access_key_id|AWSAccessKeyId)\s*=\s*(.+)$", line)
            if parse_access is not None:
                access = parse_access.group(2)
            parse_secret = re.match(r"(aws_secret_access_key|AWSSecretKey)\s*=\s*(.+)$", line)
            if parse_secret is not None:
                secret = parse_secret.group(2)
    if access is None:
        return {"error": "awsfile did not contain access ID"}
    if secret is None:
        return {"error": "awsfile did not contain secret key"}
    return {"access": access, "secret": secret}

if __name__ == "__main__":
    print(get_site_admin_token())
