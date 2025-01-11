import authx.auth
import os
import re
import jwt
import requests


def is_default_site_admin_set():
    if os.getenv("DEFAULT_SITE_ADMIN_USER") is not None:
        result, status_code = authx.auth.get_service_store_secret("opa", key=f"site_roles")
        if status_code == 200:
            if 'admin' in result['site_roles']:
                return os.getenv("DEFAULT_SITE_ADMIN_USER") in ",".join(result['site_roles']['admin'])
        raise Exception(f"ERROR: Unable to list site administrators {result} {status_code}")
    return False


def get_user_name(token):
    user_key = os.getenv("CANDIG_USER_KEY")
    decoded_jwt = jwt.decode(token, options={"verify_signature": False})
    if decoded_jwt is not None and user_key is not None and user_key in decoded_jwt:
        return decoded_jwt[user_key]
    return None


def is_site_admin(token):
    if (authx.auth.is_site_admin(None, token=token)):
        return True
    return False


def get_refresh_token(token):
    client_secret = authx.auth.get_service_store_secret(service="keycloak", key="client-secret")
    return authx.auth.get_oauth_response(
        client_secret = client_secret,
        refresh_token=token
        )

#####
# AWS stuff
#####

def get_minio_client(token, s3_endpoint, bucket, access_key=None, secret_key=None, region=None, secure=True):
    return authx.auth.get_minio_client(token=token, s3_endpoint=s3_endpoint, bucket=bucket, access_key=access_key, secret_key=secret_key, region=region, secure=secure)


def parse_s3_credential(awsfile):
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
