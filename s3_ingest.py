import sys
import argparse
import json
import requests
import os
import auth
from pathlib import Path


CANDIG_URL = os.getenv("CANDIG_URL", "")


def main():
    parser = argparse.ArgumentParser(description="Script to ingest files into an S3-compatible bucket.")
    
    parser.add_argument("--sample", help="file name of sample", required=False)
    parser.add_argument("--samplefile", help="file with list of file names of samples", required=False)
    parser.add_argument("--endpoint", help="s3 endpoint")
    parser.add_argument("--bucket", help="s3 bucket name")
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
        
    # parse the awsfile:
    result = auth.parse_aws_credential(args.awsfile)
    if "error" in result:
        raise Exception(f"Failed to parse awsfile: {result['error']}")
    client = auth.get_minio_client(args.endpoint, args.bucket, access_key=result["access"], secret_key=result["secret"])

    for sample in samples:
        file = Path(sample)
        with open(file, "rb") as fp:
            result = client["client"].put_object(args.bucket, file.name, fp, file.stat().st_size)
            print(f"uploaded {result.object_name}")


if __name__ == "__main__":
    main()
