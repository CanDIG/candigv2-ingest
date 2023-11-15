import argparse

import auth
import os
import re
import json
from ingest_result import IngestServerException, IngestUserException, IngestResult
import requests
from urllib.parse import urlparse


CANDIG_URL = os.getenv("CANDIG_URL", "")
HTSGET_URL = CANDIG_URL + "/genomics"
HOSTNAME = HTSGET_URL.replace(f"{urlparse(CANDIG_URL).scheme}://","")


def link_genomic_data(headers, sample):
    url = f"{HTSGET_URL}/ga4gh/drs/v1/objects"

    # get the master genomic object, or create it:
    genomic_drs_obj = {
        "id": sample["genomic_id"],
        "name": sample["genomic_id"],
        "description": sample["metadata"]["sequence_type"],
        "cohort": sample["program_id"],
        "reference_genome": sample["metadata"]["reference"],
        "version": "v1",
        "contents": []
    }
    response = requests.get(f"{url}/{sample['genomic_id']}", headers=headers)
    if response.status_code == 200:
        genomic_drs_obj = response.json()

    # add GenomicDataDrsObject to contents
    add_file_drs_object(genomic_drs_obj, sample["main"], sample["metadata"]["data_type"], headers)

    if "index" in sample:
        # add GenomicIndexDrsObject to contents
        add_file_drs_object(genomic_drs_obj, sample["index"], "index", headers)

    for clin_sample in sample["samples"]:
        # for each sample in the samples, get the SampleDrsObject or create it
        sample_drs_obj = {
            "id": clin_sample["donor_sample_id"],
            "name": clin_sample["donor_sample_id"],
            "description": "sample",
            "cohort": sample["program_id"],
            "version": "v1",
            "contents": []
        }
        response = requests.get(f"{url}/{clin_sample['donor_sample_id']}", headers=headers)
        if response.status_code == 200:
            sample_drs_obj = response.json()

        # add the GenomicDrsObject to its contents, if it's not already there:
        not_found = True
        if len(sample_drs_obj["contents"]) > 0:
            for obj in sample_drs_obj["contents"]:
                if obj["name"] == clin_sample["donor_sample_id"]:
                    not_found = False
        if not_found:
            contents_obj = {
                "name": sample["genomic_id"],
                "id": sample["genomic_id"],
                "drs_uri": [f"{HOSTNAME}/{sample['genomic_id']}"]
            }
            sample_drs_obj["contents"].append(contents_obj)

        # update the sample_drs_object in the database:
        response = requests.post(f"{url}", json=sample_drs_obj, headers=headers)
        if response.status_code != 200:
            return response

        # then add the sample to the GenomicDrsObject's contents, if it's not already there:
        not_found = True
        if len(genomic_drs_obj["contents"]) > 0:
            for obj in genomic_drs_obj["contents"]:
                if obj["name"] == clin_sample["donor_sample_id"]:
                    not_found = False
        if not_found:
            contents_obj = {
                "name": clin_sample["donor_sample_id"],
                "id": clin_sample["genomic_sample_id"],
                "drs_uri": [f"{HOSTNAME}/{clin_sample['donor_sample_id']}"]
            }
            genomic_drs_obj["contents"].append(contents_obj)

    # finally, post the genomic_drs_object
    response = requests.post(url, json=genomic_drs_obj, headers=headers)
    return response


def add_file_drs_object(genomic_drs_obj, file, type, headers):
    url = f"{HTSGET_URL}/ga4gh/drs/v1/objects"
    # is this file already in the master object?:
    not_found = True
    if len(genomic_drs_obj["contents"]) > 0:
        for obj in genomic_drs_obj["contents"]:
            if obj["name"] == file["name"]:
                not_found = False
    if not_found:
        # look for this file in htsget:
        response = requests.get(f"{url}/{file['name']}", headers=headers)
        print(f"GET {file['name']}: {response.status_code} {response.text}")
        if response.status_code == 404:
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
                obj["access_methods"].append(access_method)
            response = requests.post(url, json=obj, headers=headers)
            if response.status_code > 200:
                return response
            else:
                contents_obj = {
                    "name": file["name"],
                    "id": type,
                    "drs_uri": [f"{HOSTNAME}/{file['name']}"]
                }
                genomic_drs_obj["contents"].append(contents_obj)


def get_access_method(url):
    if url.startswith("s3"):
        return {
            "type": "s3",
            "access_id": url.replace("s3://", "")
        }
    elif url.startswith("file"):
        return {
            "type": "file",
            "access_url": {
                "url": url
            }
        }
    return None


def htsget_ingest(ingest_json, headers):
    result = {
        "errors": [],
        "results": []
    }
    status_code = 200
    for sample in ingest_json:
        # validate the access method

        # create the corresponding DRS objects
        response = link_genomic_data(headers, sample)
        if (response.status_code > 200):
            if response.status_code < 500:
                result["errors"].append(response.text)
            else:
                result["errors"].append(response.text)
        result["results"].append(sample["genomic_id"])
    return result, status_code

def main():
    parser = argparse.ArgumentParser(description="A script that ingests a sample vcf and its index into htsget.")
    parser.add_argument("--samplefile", help="A file specifying a genomic sample", required=True)

    args = parser.parse_args()

    genomic_input = []
    if args.samplefile:
        with open(args.samplefile) as f:
            genomic_input = json.loads(f.read())
    if len(genomic_input) == 0:
        return "No samples to ingest"
    result = htsget_ingest(genomic_input, auth.get_auth_header())
    print(json.dumps(result, indent=4))

if __name__ == "__main__":
    main()