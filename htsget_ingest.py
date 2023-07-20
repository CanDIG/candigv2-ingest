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

def collect_samples_for_genomic_id(genomic_id, client, genomic_files={}, prefix=""):
    # If genomic_files is provided, it means the filenames do not correspond to the genomic_id names in the bucket
    # And have been provided manually.
    files = []
    samples = []
    if genomic_files:
        sample = genomic_files["sample"]
        index = genomic_files["index"]
        index_pattern = re.compile(f"({prefix}(.+?))(\.tbi|\.bai|\.crai|\.csi)$")
        index_parse = index_pattern.match(index)
        type = 'read'
        if index_parse.group(3) == '.tbi':
            type = 'variant'
        samples.append(
            {
                "id": genomic_id,
                "file": sample,
                "index": index,
                "type": type,
                "file_access": f"{client['endpoint']}/{client['bucket']}/{prefix}{sample}",
                "index_access": f"{client['endpoint']}/{client['bucket']}/{prefix}{index}"
            }
        )
    else:
        # first, find all files that are related to this sample at the endpoint:
        files_iterator = client['client'].list_objects(client["bucket"], prefix=prefix+genomic_id)
        for f in files_iterator:
            files.append(f.object_name)
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
                samples.append(
                    {
                        "id": genomic_id,
                        "file": file,
                        "index": index,
                        "type": type,
                        "file_access": f"{client['endpoint']}/{client['bucket']}/{prefix}{file}",
                        "index_access": f"{client['endpoint']}/{client['bucket']}/{prefix}{index}"
                    }
                )
    return samples

def collect_samples_for_genomic_id_local(sample):
    if not sample["files"]:
        return IngestUserException("Samples must specify filenames for local ingest")

    file = sample["files"]["sample"]
    index = sample["files"]["index"]
    index_pattern = re.compile(f"(.+?)(\.tbi|\.bai|\.crai|\.csi)$")
    index_parse = index_pattern.match(index)
    if not index_parse:
        return IngestUserException("Index invalid or not provided for sample %s" % sample["genomic_id"])
    type = 'read'
    if index_parse.group(2) == '.tbi':
        type = 'variant'
    return [{
            "id": sample["genomic_id"],
            "file": os.path.basename(file),
            "index": os.path.basename(index),
            "type": type,
            "file_access": f"file://{file}",
            "index_access": f"file://{file}"
        }]

def htsget_ingest_from_file(dataset, token, samples, reference="hg38", indexing=False):
    if os.getenv("CANDIG_URL") == "":
        raise Exception("CANDIG_URL environment variable is not set")

    created = []
    for sample in samples:
        if ((type(sample) != dict) or ("genomic_id" not in sample) or ("clinical_id" not in sample)):
            return IngestUserException("Invalid sample data provided - see candigv2-ingest README.md")
        if "files" not in sample:
            sample["files"] = None
        objects_to_create = collect_samples_for_genomic_id_local(sample)
        if isinstance(objects_to_create, IngestResult):
            return objects_to_create # An error occurred
        if len(objects_to_create) == 0:
            return IngestUserException("Sample file invalid: %s" % sample["genomic_id"])
        response = post_objects(sample["genomic_id"], objects_to_create, token, clinical_id=sample["clinical_id"],
                                ref_genome=reference,
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


def htsget_ingest_from_bucket(endpoint, bucket, dataset, token,
                          samples, awsfile=None, access=None, secret=None, prefix="", reference="hg38", indexing=False):
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
    for sample in samples:
        if ((type(sample) != dict) or ("genomic_id" not in sample)):
            return IngestUserException("Invalid sample data provided - see candigv2-ingest README.md")
        if "files" not in sample:
            sample["files"] = None
        if "clinical_id" not in sample:
            sample["clinical_id"] = None
        # first, find all of the s3 objects related to this sample:
        objects_to_create = collect_samples_for_genomic_id(sample["genomic_id"], client, sample["files"], prefix=prefix)
        if isinstance(objects_to_create, IngestResult):
            return objects_to_create # An error occurred
        if len(objects_to_create) == 0:
            return IngestUserException("S3 bucket or sample list must not be empty")
        response = post_objects(sample["genomic_id"], objects_to_create, token, clinical_id=sample["clinical_id"], ref_genome=reference,
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


    req_values_s3 = {
        "endpoint": "required",
        "bucket": "required",
        "dataset": "required",
        "samples": "required",
        "access": "required",
        "secret": "required",
        "prefix": "",
        "reference": "hg38",
        "indexing": False,
    }

    req_values_local = {
        "dataset": "required",
        "samples": "required",
        "reference": "hg38",
        "indexing": False,
    }
    local = False
    if ("local" in request.json):
        if (request.json["local"]):
            local = True
        request.json.pop("local")
    if not local:
        for arg in req_values_s3:
            try:
                req_values_s3[arg] = request.json[arg]
            except KeyError:
                if (req_values_s3[arg] == "required"):
                    return {"result": "Parameter %s is required" % arg}, 400
        req_values_s3["token"] = token
        for arg in request.json:
            if arg not in req_values_s3:
                return {"result": "Invalid parameter: %s" % arg}
    else:
        for arg in req_values_local:
            try:
                req_values_local[arg] = request.json[arg]
            except KeyError:
                if (req_values_local[arg] == "required"):
                    return {"result": "Parameter %s is required" % arg}, 400
        req_values_local["token"] = token
        for arg in request.json:
            if arg not in req_values_local:
                return {"result": "Invalid parameter: %s" % arg}

    try:
        if not local:
            response = htsget_ingest_from_bucket(**req_values_s3)
        else:
            response = htsget_ingest_from_file(**req_values_local)
    except Exception as e:
        traceback.print_exc()
        return {"result": "Unknown error: %s" % str(e)}, 500

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

    parser.add_argument("--local", help="Ingest from local directory", action='store_true', required=False)
    parser.add_argument("--samplefile", help="A file specifying genomic/clinical IDs to ingest and optionally their filenames")
    parser.add_argument("--endpoint", help="s3 endpoint", required=False)
    parser.add_argument("--bucket", help="s3 bucket name", required=False)
    parser.add_argument("--dataset", help="dataset name", required=True)
    parser.add_argument("--awsfile", help="s3 credentials", required=False)
    parser.add_argument("--access", help="access key", required=False)
    parser.add_argument("--secret", help="secret key", required=False)
    parser.add_argument("--region", help="optional: s3 region", required=False)
    parser.add_argument("--prefix", help="optional: s3 prefix", required=False, default="")
    parser.add_argument("--reference", help="optional: reference genome, either hg37 or hg38", required=False, default="hg38")
    parser.add_argument("--indexing", action="store_true", help="optional: force re-indexing", required=False)

    args = parser.parse_args()

    if args.samplefile:
        with open(args.samplefile) as f:
            genomic_samples = json.loads(f.read())

    if args.local:
        result = htsget_ingest_from_file(args.dataset, auth.get_bearer_from_refresh(auth.get_site_admin_token()),
                                         genomic_samples, args.reference, args.indexing)
    else:
        result = htsget_ingest_from_bucket(args.endpoint, args.bucket, args.dataset,
                                        auth.get_bearer_from_refresh(auth.get_site_admin_token()),
                                        genomic_samples, args.awsfile,
                                        args.access, args.secret, args.prefix, args.reference,
                                        args.indexing)
    if result.value:
      print(result.value)

if __name__ == "__main__":
    main()
