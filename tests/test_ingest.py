import pytest
import json
import requests
import os
import re
import sys

REPO_DIR = os.path.abspath(f"{os.path.dirname(os.path.realpath(__file__))}/..")
sys.path.insert(0, os.path.abspath(f"{REPO_DIR}"))
import katsu_ingest
import htsget_ingest

CANDIG_URL = os.getenv("CANDIG_URL", "http://localhost")
HTSGET_URL = CANDIG_URL + "/genomics"


def test_prepare_clinical_ingest():
    with open("tests/clinical_ingest.json", "r") as f:
        data = json.load(f)
        result = katsu_ingest.prepare_clinical_data_for_ingest(data)
        print(json.dumps(result, indent=4))
        assert len(result) == 2
        assert len(result["SYNTH_02"]["schemas"]["systemic_therapies"]) == 20


def callback(request, context):
    return request.json()

def verify_callback(request, context):
    return {"result": True}

def test_htsget_ingest(requests_mock):
    matcher = re.compile(f"{HTSGET_URL}/ga4gh/drs/v1/objects/.+")
    requests_mock.post(f"{HTSGET_URL}/ga4gh/drs/v1/objects", json=callback, status_code=200)
    requests_mock.get(matcher, status_code=404)
    matcher = re.compile(f"{HTSGET_URL}/htsget/v1/variants/.+/index")
    requests_mock.get(matcher, status_code=200)
    matcher = re.compile(f"{HTSGET_URL}/htsget/v1/variants/.+/verify")
    requests_mock.get(matcher, json=verify_callback, status_code=200)
    matcher = re.compile(f"{HTSGET_URL}/htsget/v1/reads/.+/index")
    requests_mock.get(matcher, status_code=200)
    matcher = re.compile(f"{HTSGET_URL}/htsget/v1/reads/.+/verify")
    requests_mock.get(matcher, json=verify_callback, status_code=200)

    headers = {"Authorization": f"Bearer test", "Content-Type": "application/json"}
    with open("tests/genomic_ingest.json", "r") as f:
        data = json.load(f)
        for sample in data:
            response = htsget_ingest.link_genomic_data(sample)
            print(json.dumps(response, indent=4))
            assert len(response["errors"]) == 0
            assert "genomic" in response
            assert len(response["genomic"]["contents"]) == 2 + len(sample["samples"])
            assert "sample" in response
            assert len(response["sample"]) == len(sample["samples"])
            assert len(response["sample"][0]["contents"]) == 1

    # bad sample:
    bad_s3_sample = {
        "program_id": "SYNTHETIC-2",
        "genomic_file_id": "bad_sample.cnv.vcf",
        "main": {
            "access_method": "s3://1000genomes/release/20130502/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz?public=true",
            "name": "bad_sample.cnv.vcf.gz"
        },
        "index": {
            "access_method": "s3://s3.us-east-1.amazonaws.com/1000genomes/release/20130502/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz.tbi?public=true",
            "name": "bad_sample.cnv.vcf.gz.tbi"
        },
        "metadata": {
            "sequence_type": "wgs",
            "data_type": "variant",
            "reference": "hg38"
        },
        "samples": [
            {
                "genomic_file_sample_id": "bad_sample",
                "submitter_sample_id": "SAMPLE_REGISTRATION_1"
            }
        ]
    }
    response = htsget_ingest.link_genomic_data(bad_s3_sample)
    print(json.dumps(response, indent=4))
    assert len(response["errors"]) == 2
