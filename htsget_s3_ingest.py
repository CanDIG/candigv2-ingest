import argparse
import auth
import os
import re
import json
from htsget_methods import post_to_dataset, get_dataset_objects, post_objects


def collect_samples_for_genomic_id(genomic_id, client, prefix=""):
    # first, find all files that are related to this sample at the endpoint:
    files_iterator = client['client'].list_objects(client["bucket"], prefix=prefix+genomic_id)
    files = []
    for f in files_iterator:
        files.append(f.object_name)
    samples = []
    while len(files) > 0:
        f = files.pop(0)
        index_pattern = re.compile(f"({prefix}(.+?))(\.tbi|\.bai|\.crai|\.csi)$")
        index_parse = index_pattern.match(f)
        if index_parse is not None: # this is a file we're interested in
            if index_parse.group(3) is not None and index_parse.group(3) != "":
                index = index_parse.group(2) + index_parse.group(3)
                # f is an index file, so it should have a corresponding file
                file = index_parse.group(2)
                if index_parse.group(1) in files:
                    files.remove(index_parse.group(1))
                type = 'read'
                if index_parse.group(3) == '.tbi':
                    type = 'variant'
                id_parse = re.match(r"(.+)\.(vcf|bam|cram|sam|bcf)(\.gz)*", file)
                samples.append(
                    {
                        "id": id_parse.group(1),
                        "file": file,
                        "index": index,
                        "type": type,
                        "file_access": f"{client['endpoint']}/{client['bucket']}/{prefix}{file}",
                        "index_access": f"{client['endpoint']}/{client['bucket']}/{prefix}{index}"
                    }
                )
    return samples


def main():
    parser = argparse.ArgumentParser(description="A script that ingests a sample vcf and its index into htsget.")

    parser.add_argument("--genomic_id", help="genomic sample id", required=False)
    parser.add_argument("--clinical_id", help="clinical sample registration id", required=False)
    parser.add_argument("--samplefile", help="file with list of genomic sample ids, optionally tab-delimited with clinical sample ids", required=False)
    parser.add_argument("--endpoint", help="s3 endpoint")
    parser.add_argument("--bucket", help="s3 bucket name")
    parser.add_argument("--dataset", help="dataset name")
    parser.add_argument("--awsfile", help="s3 credentials", required=False)
    parser.add_argument("--access", help="access key", required=False)
    parser.add_argument("--secret", help="secret key", required=False)
    parser.add_argument("--region", help="optional: s3 region", required=False)
    parser.add_argument("--prefix", help="optional: s3 prefix", required=False, default="")
    parser.add_argument("--reference", help="optional: reference genome, either hg37 or hg38", required=False, default="hg38")
    parser.add_argument('--indexing', action="store_true", help="optional: force re-indexing")

    args = parser.parse_args()

    genomic_samples = []
    clinical_samples = []
    if args.samplefile is not None:
        with open(args.samplefile) as f:
            lines = f.readlines()
            for line in lines:
                parts = line.strip().split()
                genomic_samples.append(parts[0])
                if len(parts) > 1:
                    clinical_samples.append(parts[1])
    elif args.genomic_id is not None:
        genomic_samples = [args.sample]
    else:
        raise Exception("Either a sample name or a file of samples is required.")

    if args.clinical_id is not None:
        clinical_samples = [args.clinical_id]

    if os.getenv("CANDIG_URL") == "":
        raise Exception("CANDIG_URL environment variable is not set")

    token = auth.get_site_admin_token()

    if args.awsfile:
        # parse the awsfile:
        result = auth.parse_aws_credential(args.awsfile)
        access_key = result["access"]
        secret_key = result["secret"]
        if "error" in result:
            raise Exception(f"Failed to parse awsfile: {result['error']}")
    elif args.access and args.secret:
        access_key = args.access
        secret_key = args.secret
    else:
        raise Exception("Either awsfile or access/secret need to be provided.")

    client = auth.get_minio_client(args.endpoint, args.bucket, access_key=access_key, secret_key=secret_key)
    result, status_code = auth.store_aws_credential(token=token, client=client)
    if status_code != 200:
        raise Exception(f"Failed to add AWS credential to vault: {result}")
    created = []
    for i in range(0, len(genomic_samples)):
        token = auth.get_site_admin_token()
        # first, find all of the s3 objects related to this sample:
        objects_to_create = collect_samples_for_genomic_id(genomic_samples[i], client, prefix=args.prefix)
        clinical_id = None
        if len(clinical_samples) == len(genomic_samples):
            clinical_id = clinical_samples[i]
        post_objects(genomic_samples[i], objects_to_create, token, clinical_id=clinical_id, ref_genome=args.reference, force=args.indexing)
        created.extend(map(lambda s : s['id'], objects_to_create))
    post_to_dataset(created, args.dataset, token)
    print(created)
    # response = get_dataset_objects(args.dataset, token)
    # print(json.dumps(response, indent=4))


if __name__ == "__main__":
    main()
