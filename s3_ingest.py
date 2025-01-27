import sys
import argparse
import json
import requests
import os
import auth
from pathlib import Path


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


def main():
    parser = argparse.ArgumentParser(description="Script to ingest files into an S3-compatible bucket.")

    parser.add_argument("--sample", help="file name of sample", required=False)
    parser.add_argument("--samplefile", help="file with list of file names of samples", required=False)
    parser.add_argument("--endpoint", help="s3 endpoint")
    parser.add_argument("--bucket", help="s3 bucket name")
    parser.add_argument("--awsfile", help="s3 credentials", required=False)
    parser.add_argument("--access", help="access key", required=False)
    parser.add_argument("--secret", help="secret key", required=False)

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

    if args.awsfile:
        # parse the awsfile:
        result = parse_s3_credential(args.awsfile)
        access_key = result["access"]
        secret_key = result["secret"]
        if "error" in result:
            raise Exception(f"Failed to parse awsfile: {result['error']}")
    elif args.access and args.secret:
        access_key = args.access
        secret_key = args.secret
    else:
        raise Exception("Either awsfile or access/secret need to be provided.")

    client = authx.auth.get_minio_client(token=auth.get_site_admin_token(), s3_endpoint=args.endpoint, bucket=args.bucket, access_key=access_key, secret_key=secret_key)

    for sample in samples:
        file = Path(sample)
        with open(file, "rb") as fp:
            result = client["client"].put_object(args.bucket, file.name, fp, file.stat().st_size)
            print(f"uploaded {result.object_name}")


if __name__ == "__main__":
    main()
