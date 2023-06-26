import argparse

import auth
import os
import re
import json
from htsget_methods import post_to_dataset, get_dataset_objects, post_objects
from ingest_result import IngestPermissionsException, IngestServerException, IngestUserException, IngestResult
import traceback


from flask import Blueprint, request

ingest_blueprint = Blueprint("ingest_genomic", __name__)


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

def htsget_ingest_from_s3(endpoint, bucket, dataset, token, genomic_id=None, clinical_id=None,
                          samples=[], awsfile=None, access=None, secret=None, prefix="", reference="hg38", sample="", indexing=False):
    genomic_samples = []
    clinical_samples = []
    if samples:
        for line in samples:
            parts = line.strip().split()
            genomic_samples.append(parts[0])
            if len(parts) > 1:
                clinical_samples.append(parts[1])
    elif (genomic_id and sample):
        genomic_samples = [sample]
    else:
        return IngestUserException("Either a sample name or a file of samples is required.")

    if clinical_id:
        clinical_samples = [clinical_id]

    if os.getenv("CANDIG_URL") == "":
        raise Exception("CANDIG_URL environment variable is not set")

    if awsfile:
        # parse the awsfile:
        result = auth.parse_aws_credential(awsfile)
        access_key = result["access"]
        secret_key = result["secret"]
        if "error" in result:
            return IngestServerException(f"Failed to parse awsfile: {result['error']}")
    elif access and secret:
        access_key = access
        secret_key = secret
    else:
        return IngestUserException("Either awsfile or access/secret need to be provided.")

    client = auth.get_minio_client(token, endpoint, bucket, access_key=access_key, secret_key=secret_key)
    result, status_code = auth.store_aws_credential(token=token, client=client)
    if status_code != 200:
        return IngestServerException(f"Failed to add AWS credential to vault: {result}")
    created = []
    for i in range(0, len(genomic_samples)):
        # first, find all of the s3 objects related to this sample:
        objects_to_create = collect_samples_for_genomic_id(genomic_samples[i], client, prefix=prefix)
        clinical_id = None
        if len(clinical_samples) == len(genomic_samples):
            clinical_id = clinical_samples[i]
        if len(objects_to_create) == 0:
            return IngestUserException("S3 bucket or sample list must not be empty")
        response = post_objects(genomic_samples[i], objects_to_create, token, clinical_id=clinical_id, ref_genome=reference,
                     force=indexing)
        if (response.status_code > 200):
            print(response.text)
            if response.status_code < 500:
                return IngestUserException(response.text)
            else:
                return IngestServerException(response.text)
        created.extend(map(lambda s: s['id'], objects_to_create))
    response = post_to_dataset(created, dataset, token)
    if response.status_code > 300:
        print(response.text)
        if response.status_code < 500:
            return IngestUserException(response.text)
        else:
            return IngestServerException(response.text)
    return IngestResult(str(created))

@ingest_blueprint.route('/ingest_genomic', methods=["POST"])
def genomic_ingest_endpoint():
    if "Authorization" not in request.headers:
        return {"result": "Refresh token required"}, 401
    try:
        refresh_token = request.headers["Authorization"].split("Bearer ")[1]
    except Exception as e:
        if "Invalid refresh token" in str(e):
            return {"result": "Refresh token invalid or unauthorized"}, 401
        return {"result": "Unknown error during authorization"}, 401
    try:
        token = auth.get_bearer_from_refresh(refresh_token)
    except Exception as e:
        return {"result": "Error validating token: %s" % str(e)}, 401


    req_values = {
        "endpoint": "required",
        "bucket": "required",
        "dataset": "required",
        "samples": [],
        "access": "required",
        "secret": "required",
        "prefix": "",
        "reference": "hg38",
        "indexing": False
    }

    for arg in req_values:
        try:
            req_values[arg] = request.json[arg]
        except KeyError:
            if req_values[arg] == "required":
                return {"result": "Parameter %s is required" % arg}, 400
    req_values["token"] = token

    try:
        response = htsget_ingest_from_s3(**req_values)
    except Exception as e:
        traceback.print_exc()
        return "Unknown error: %s" % str(e), 500

    if type(response) == IngestResult:
        return {"result": "Ingested genomic samples: %s" % response.value}, 200
    elif type(response) == IngestUserException:
        return {"result": "Data error: %s" % response.value}, 400
    elif type(response) == IngestPermissionsException:
        return {"result": "Error: You are not authorized to write to program." % response.value}, 403
    elif type(response) == IngestServerException:
        return {"result": "Ingest encountered the following errors: %s" % response.value}, 500
    return 500


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
    parser.add_argument('--sample', action="store_true", help="optional: name of sample if genomic id is provided")

    args = parser.parse_args()

    if args.samplefile:
        with open(args.samplefile) as f:
            samples = f.readlines()
    else:
        samples = None

    result = htsget_ingest_from_s3(args.endpoint, args.bucket, args.dataset,
                                    auth.get_bearer_from_refresh(auth.get_site_admin_token()),
                                     args.genomic_id, args.clinical_id, samples, args.awsfile,
                                     args.access, args.secret, args.prefix, args.reference, args.sample,
                                     args.indexing)
    if result.value:
      print(result.value)

if __name__ == "__main__":
    main()
