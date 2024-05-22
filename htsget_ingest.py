import argparse

from authx.auth import get_site_admin_token
import os
import re
import json
from ingest_result import IngestServerException, IngestUserException, IngestResult
import requests
import sys
from urllib.parse import urlparse
from clinical_etl.schema import openapi_to_jsonschema
import jsonschema


CANDIG_URL = os.getenv("CANDIG_URL", "")
HTSGET_URL = os.getenv("HTSGET_URL", f"{CANDIG_URL}/genomics")
DRS_HOST_URL = "drs://" + CANDIG_URL.replace(f"{urlparse(CANDIG_URL).scheme}://","") + "/genomics"


def link_genomic_data(headers, sample):
    url = f"{HTSGET_URL}/ga4gh/drs/v1/objects"
    result = {
        "errors": []
    }

    # get the master genomic object, or create it:
    genomic_drs_obj = {}
    response = requests.get(f"{url}/{sample['genomic_file_id']}", headers=headers)
    if response.status_code == 200:
        genomic_drs_obj = response.json()
    genomic_drs_obj["id"] = sample["genomic_file_id"]
    genomic_drs_obj["name"] = sample["genomic_file_id"]
    genomic_drs_obj["description"] = sample["metadata"]["sequence_type"]
    genomic_drs_obj["cohort"] = sample["program_id"]
    genomic_drs_obj["reference_genome"] = sample["metadata"]["reference"]
    genomic_drs_obj["version"] = "v1"
    if "contents" not in genomic_drs_obj:
        genomic_drs_obj["contents"] = []

    # add GenomicDataDrsObject to contents
    response = add_file_drs_object(genomic_drs_obj, sample["main"], sample["metadata"]["data_type"], headers)
    if "error" in response:
        result["errors"].append(response["error"])

    if "index" in sample:
        # add GenomicIndexDrsObject to contents
        response = add_file_drs_object(genomic_drs_obj, sample["index"], "index", headers)
        if "error" in response:
            result["errors"].append(response["error"])

    result["sample"] = []
    for clin_sample in sample["samples"]:
        # for each sample in the samples, get the SampleDrsObject or create it
        sample_drs_obj = {
            "id": clin_sample["submitter_sample_id"],
            "name": clin_sample["submitter_sample_id"],
            "description": "sample",
            "cohort": sample["program_id"],
            "version": "v1",
            "contents": []
        }
        response = requests.get(f"{url}/{clin_sample['submitter_sample_id']}", headers=headers)
        if response.status_code == 200:
            sample_drs_obj = response.json()

        # add the GenomicDrsObject to its contents, if it's not already there:
        not_found = True
        if len(sample_drs_obj["contents"]) > 0:
            for obj in sample_drs_obj["contents"]:
                if obj["name"] == sample["genomic_file_id"]:
                    not_found = False
        if not_found:
            contents_obj = {
                "name": sample["genomic_file_id"],
                "id": sample["genomic_file_id"],
                "drs_uri": [f"{DRS_HOST_URL}/{sample['genomic_file_id']}"]
            }
            sample_drs_obj["contents"].append(contents_obj)

        # update the sample_drs_object in the database:
        response = requests.post(f"{url}", json=sample_drs_obj, headers=headers)
        if response.status_code != 200:
            result["errors"].append({"error": f"error creating sample drs object {sample_drs_obj['id']}: {response.status_code} {response.text}"})
        else:
            result["sample"].append(response.json())

        # then add the sample to the GenomicDrsObject's contents, if it's not already there:
        contents_obj = {
            "name": clin_sample["submitter_sample_id"],
            "id": clin_sample["genomic_file_sample_id"],
            "drs_uri": [f"{DRS_HOST_URL}/{clin_sample['submitter_sample_id']}"]
        }
        not_found = True
        if len(genomic_drs_obj["contents"]) > 0:
            for i in range(0, len(genomic_drs_obj["contents"])):
                if genomic_drs_obj["contents"][i]["name"] == clin_sample["submitter_sample_id"]:
                    not_found = False
                    genomic_drs_obj["contents"][i] = contents_obj
                    break
        if not_found:
            genomic_drs_obj["contents"].append(contents_obj)
    if len(result["sample"]) == 0:
            result.pop("sample")

    # finally, post the genomic_drs_object
    response = requests.post(url, json=genomic_drs_obj, headers=headers)
    if response.status_code != 200:
        result["errors"].append({"error": f"error posting genomic drs object {genomic_drs_obj['id']}: {response.status_code} {response.text}"})
    else:
        result["genomic"] = response.json()

    # verify that the genomic file exists and is readable
    verify_url = f"{HTSGET_URL}/htsget/v1/{sample['metadata']['data_type']}s/{genomic_drs_obj['id']}/verify"

    response = requests.get(verify_url, headers=headers)
    if response.status_code != 200:
        result["errors"].append({"error": f"could not verify sample: {response.text}"})
    elif not response.json()['result']:
        result["errors"].append({"error": f"could not verify sample: {response.json()['message']}"})
    else:
        # flag the genomic_drs_object for indexing:
        url =f"{HTSGET_URL}/htsget/v1/{sample['metadata']['data_type']}s/{genomic_drs_obj['id']}/index"
        response = requests.get(url, headers=headers)
    return result


def add_file_drs_object(genomic_drs_obj, file, type, headers):
    url = f"{HTSGET_URL}/ga4gh/drs/v1/objects"
    obj = {
        "access_methods": [],
        "id": file['name'],
        "name": file['name'],
        "description": type,
        "cohort": genomic_drs_obj["cohort"],
        "version": "v1"
    }
    access_method = get_access_method(file["access_method"])
    if access_method is not None:
        if "message" in access_method:
            return {"error": access_method["message"]}
        obj["access_methods"].append(access_method)
    contents_obj = {
        "name": file["name"],
        "id": type,
        "drs_uri": [f"{DRS_HOST_URL}/{file['name']}"]
    }

    # is this file already in the master object? If so, replace it:
    not_found = True
    if len(genomic_drs_obj["contents"]) > 0:
        for i in range(0, len(genomic_drs_obj["contents"])):
            if genomic_drs_obj["contents"][i]["name"] == file["name"]:
                genomic_drs_obj["contents"][i] = contents_obj
                not_found = False
                break
    if not_found:
        genomic_drs_obj["contents"].append(contents_obj)
    response = requests.post(url, json=obj, headers=headers)
    if response.status_code > 200:
        return {"error": f"error creating file drs object: {response.status_code} {response.text}"}
    return contents_obj


def get_access_method(url):
    if url.startswith("file"):
        return {
            "type": "file",
            "access_url": {
                "url": url
            }
        }
    try:
        result = parse_s3_url(url)
    except Exception as e:
        return {
            "message": str(e)
        }
    return {
        "type": "s3",
        "access_id": url
    }


def parse_s3_url(url):
    """
    Parse a url into s3 components
    """
    s3_url_parse = re.match(r"((https*|s3):\/\/(.+?))\/(.+)", url)
    if s3_url_parse is not None:
        if s3_url_parse.group(2) == "s3":
            raise Exception(f"Incorrect URL format {url}. S3 URLs should be in the form http(s)://endpoint-url/bucket-name/object. If your object is stored at AWS S3, you can find more information about endpoint URLs at https://docs.aws.amazon.com/general/latest/gr/rande.html")
        endpoint = s3_url_parse.group(1)
        bucket_parse = re.match(r"(.+?)\/(.+)", s3_url_parse.group(4))
        if bucket_parse is not None:
            return {
                "endpoint": endpoint,
                "bucket": bucket_parse.group(1),
                "object": bucket_parse.group(2)
            }
        raise Exception(f"S3 URI {url} does not contain a bucket name")
    raise Exception(f"URI {url} cannot be parsed as an S3-style URI")


def htsget_ingest(ingest_json, headers):
    with open("ingest_openapi.yaml") as f:
        openapi_text = f.read()
        json_schema = openapi_to_jsonschema(openapi_text, "GenomicSample")
    result = {
        "errors": {},
        "results": {}
    }
    status_code = 200
    for sample in ingest_json:
        result["errors"][sample["genomic_file_id"]] = []
        # validate the json
        if sample["genomic_file_id"] == sample["main"]["name"] or sample["genomic_file_id"] == sample["index"]["name"]:
            result["errors"][sample["genomic_file_id"]].append(f"Sample {sample['genomic_file_id']} cannot have the same name as one of its files.")
        else:
            for error in jsonschema.Draft202012Validator(json_schema).iter_errors(sample):
                result["errors"][sample["genomic_file_id"]].append(f"{' > '.join(error.path)}: {error.message}")
        if len(result["errors"][sample["genomic_file_id"]]) > 0:
            continue

        # create the corresponding DRS objects
        if "samples" not in sample or len(sample["samples"]) == 0:
            result["errors"][sample["genomic_file_id"]].append("No samples were specified for the genomic file mapping")
            break
        response = link_genomic_data(headers, sample)
        for err in response["errors"]:
            result["errors"][sample["genomic_file_id"]].append(err)
            if "403" in err:
                status_code = 403
                break
        if len(result["errors"][sample["genomic_file_id"]]) == 0:
            result["errors"].pop(sample["genomic_file_id"])
        response.pop("errors")
        if len(response) > 0:
            result["results"][sample["genomic_file_id"]] = response
    return result, status_code


def main():
    parser = argparse.ArgumentParser(description="A script that ingests genomic data into htsget.")
    parser.add_argument("--samplefile", required=True,
                        help="A file specifying the location and sample linkages for one or more genomic files")

    args = parser.parse_args()

    genomic_input = []
    if args.samplefile:
        with open(args.samplefile) as f:
            genomic_input = json.loads(f.read())
    if len(genomic_input) == 0:
        return "No samples to ingest"
    token = get_site_admin_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    result, status_code = htsget_ingest(genomic_input, headers)
    print(json.dumps(result, indent=4))

if __name__ == "__main__":
    main()
