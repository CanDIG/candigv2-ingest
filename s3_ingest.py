import sys
import argparse
import json
import requests
import os
import auth
from pathlib import Path


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
        result = auth.parse_s3_credential(args.awsfile)
        access_key = result["access"]
        secret_key = result["secret"]
        if "error" in result:
            raise Exception(f"Failed to parse awsfile: {result['error']}")
    elif args.access and args.secret:
        access_key = args.access
        secret_key = args.secret
    else:
        raise Exception("Either awsfile or access/secret need to be provided.")

    client = auth.get_minio_client(auth.get_site_admin_token(), args.endpoint, args.bucket, access_key=access_key, secret_key=secret_key)

    for sample in samples:
        file = Path(sample)
        with open(file, "rb") as fp:
            result = client["client"].put_object(args.bucket, file.name, fp, file.stat().st_size)
            print(f"uploaded {result.object_name}")


if __name__ == "__main__":
    main()
