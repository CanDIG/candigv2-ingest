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
    print(endpoint)

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
                
    return {
        "endpoint": endpoint,
        "client": client, 
        "bucket": bucket,
        "access": access_key,
        "secret": secret_key
    }


if __name__ == "__main__":
    print(get_site_admin_token())
