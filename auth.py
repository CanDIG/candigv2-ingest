import authx.auth
import re


AUTH = True


def get_auth_header():
    if AUTH:
        import auth
        token = auth.get_site_admin_token()
        return {"Authorization": f"Bearer {token}"}
    return ""


def get_site_admin_token():
    return authx.auth.get_site_admin_token()


def get_minio_client(s3_endpoint, bucket, access_key=None, secret_key=None, region=None):
    return authx.auth.get_minio_client(s3_endpoint, bucket, access_key, secret_key, region)


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


def store_aws_credential(client, token):
    return authx.auth.store_aws_credential(client, token)


if __name__ == "__main__":
    print(get_site_admin_token())
