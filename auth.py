import authx.auth


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
    return authx.auth.parse_aws_credential(awsfile)


def store_aws_credential(client, token):
    return authx.auth.store_aws_credential(client, token)


if __name__ == "__main__":
    print(get_site_admin_token())
