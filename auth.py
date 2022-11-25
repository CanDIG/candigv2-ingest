import authx.auth
import os
import re


AUTH = True


def get_auth_header():
    if AUTH:
        import auth
        token = auth.get_site_admin_token()
        return {"Authorization": f"Bearer {token}"}
    return ""


def get_site_admin_token():
    return authx.auth.get_access_token(
    keycloak_url=os.getenv('KEYCLOAK_PUBLIC_URL'),
    client_id=os.getenv('CANDIG_CLIENT_ID'),
    client_secret=os.getenv('CANDIG_CLIENT_SECRET'),
    username=os.getenv('CANDIG_SITE_ADMIN_USER'),
    password=os.getenv('CANDIG_SITE_ADMIN_PASSWORD')
    )


def get_minio_client(s3_endpoint, bucket, access_key=None, secret_key=None, region=None):
    return authx.auth.get_minio_client(token=get_site_admin_token(), s3_endpoint=s3_endpoint, bucket=bucket, access_key=access_key, secret_key=secret_key, region=region)


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


def store_aws_credential(endpoint=None, bucket=None, access=None, secret=None):
    result, status_code = authx.auth.store_aws_credential(endpoint=endpoint, bucket=bucket, access=access, secret=secret)
    return status_code == 200


if __name__ == "__main__":
    print(get_site_admin_token())
