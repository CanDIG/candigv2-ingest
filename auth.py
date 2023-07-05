import authx.auth
import os
import re
import json

import requests


AUTH = True

def get_auth_header(refresh_token=None):
    if AUTH:
        import auth
        if refresh_token:
            refresh_token = auth.get_refresh_token(refresh_token)
        else:
            refresh_token = auth.get_site_admin_token()
        token = get_bearer_from_refresh(refresh_token)
        return {"Authorization": f"Bearer {token}", "refresh_token": refresh_token}
    return ""


def get_site_admin_token():
    '''
    Returns a Keycoak *refresh* token for the site admin.
    This can be transformed into a bearer token through get_bearer_from_refresh.
    '''
    return authx.auth.get_refresh_token(
    keycloak_url=os.getenv('KEYCLOAK_PUBLIC_URL'),
    client_id=os.getenv('CANDIG_CLIENT_ID'),
    client_secret=os.getenv('CANDIG_CLIENT_SECRET'),
    username=os.getenv('CANDIG_SITE_ADMIN_USER'),
    password=os.getenv('CANDIG_SITE_ADMIN_PASSWORD')
    )

def get_bearer_from_refresh(refresh_token):
    '''
    Transforms a refresh token into a usable bearer token through keycloak.
    Args:
        refresh_token: A Keycloak refresh token.
    Returns: A keycloak bearer token.
    '''
    return authx.auth.get_access_token(keycloak_url=os.getenv('KEYCLOAK_PUBLIC_URL'),
                                       client_id=os.getenv("CANDIG_CLIENT_ID"),
                                       client_secret=os.getenv('CANDIG_CLIENT_SECRET'),
                                       refresh_token=refresh_token)

def get_refresh_token(username=None, password=None, refresh_token=None):
    '''
    Returns a fresh Keycloak refresh token from either a username/password or existing refresh token.
    Args:
        username: If refresh token is not provided, a Keycloak username.
        password: If refresh token is not provided, a Keycloak password.
        refresh_token: If username/password are not provided, a Keycloak refresh token.

    Returns: A new Keycloak refresh token.

    '''
    if refresh_token:
        return authx.auth.get_refresh_token(
            keycloak_url=os.getenv('KEYCLOAK_PUBLIC_URL'),
            client_id=os.getenv('CANDIG_CLIENT_ID'),
            client_secret=os.getenv('CANDIG_CLIENT_SECRET'),
            refresh_token=refresh_token
        )
    if (username and password):
        return authx.auth.get_refresh_token(
            keycloak_url=os.getenv('KEYCLOAK_PUBLIC_URL'),
            client_id=os.getenv('CANDIG_CLIENT_ID'),
            client_secret=os.getenv('CANDIG_CLIENT_SECRET'),
            username=os.getenv(username),
            password=os.getenv(password)
        )
    else:
        raise ValueError("Username and password or refresh token required")


def get_minio_client(token, s3_endpoint, bucket, access_key=None, secret_key=None, region=None, secure=True):
    return authx.auth.get_minio_client(token=token, s3_endpoint=s3_endpoint, bucket=bucket, access_key=access_key, secret_key=secret_key, region=region, secure=secure)


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


def store_aws_credential(token=None, client=None):
    if token is None:
        token = get_site_admin_token()
    if client is None:
        return {"error": "No client provided"}, 500
    print(client)
    return authx.auth.store_aws_credential(token=token, endpoint=client["endpoint"], bucket=client["bucket"], access=client["access"], secret=client["secret"])

def is_authed(request: requests.Request):
    if 'Authorization' not in request.headers:
        return False
    request_object = json.dumps({
        "url": request.url,
        "method": request.method,
        "headers": request.headers,
        "data": request.data
    })
    if (authx.auth.is_permissible(request_object)): return True
    return False

if __name__ == "__main__":
    print(get_site_admin_token())
