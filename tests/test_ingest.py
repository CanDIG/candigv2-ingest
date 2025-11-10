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
HTSGET_URL = os.getenv("HTSGET_URL", f"{CANDIG_URL}/genomics")
DRS_URL = os.getenv("DRS_URL", f"{CANDIG_URL}/drs")
VAULT_URL = os.getenv("VAULT_URL", f"{CANDIG_URL}/vault")
RNAGET_URL = os.getenv("RNAGET_URL", f"{CANDIG_URL}/rnaget")



def test_prepare_clinical_ingest():
    with open("tests/clinical_ingest.json", "r") as f:
        data = json.load(f)
        result = katsu_ingest.prepare_clinical_data_for_ingest(data)
        print(json.dumps(result, indent=4))
        assert len(result) == 1
        assert len(result["SYNTH_01"]["schemas"]["systemic_therapies"]) == 16


def callback(request, context):
    return request.json()

def verify_callback(request, context):
    return {"result": True}

def test_htsget_ingest(requests_mock):
    matcher = re.compile(f"{DRS_URL}/ga4gh/drs/v1/objects/.+")
    requests_mock.post(f"{DRS_URL}/ga4gh/drs/v1/objects", json=callback, status_code=200)
    requests_mock.get(matcher, status_code=200, json={"id": "sdfs", "name": "sfdfs", "contents": []})
    matcher = re.compile(f"{HTSGET_URL}/htsget/v1/.+/index")
    requests_mock.get(matcher, status_code=200)
    matcher = re.compile(f"{HTSGET_URL}/htsget/v1/.+/verify")
    requests_mock.get(matcher, json=verify_callback, status_code=200)
    matcher = re.compile(f"{HTSGET_URL}/htsget/v1/reads/.+/index")
    requests_mock.get(matcher, status_code=200)
    matcher = re.compile(f"{HTSGET_URL}/htsget/v1/reads/.+/verify")
    requests_mock.get(matcher, json=verify_callback, status_code=200)
    requests_mock.post(f"{VAULT_URL}/v1/auth/approle/role/candig-ingest/secret-id", json={"data": {"secret_id": "sfsfd"}}, status_code=200)
    requests_mock.post(f"{VAULT_URL}/v1/auth/approle/login", json={"auth": {"client_token": "sfsfd"}}, status_code=200)
    matcher = re.compile(f"{VAULT_URL}/v1/candig-ingest/token/.+")
    requests_mock.get(matcher, json={"data": {"client_token": "sfsfd"}}, status_code=200)
    requests_mock.post(matcher, json={"data": {"client_token": "sfsfd"}}, status_code=200)

    matcher = re.compile(f"{RNAGET_URL}/.+")
    requests_mock.post(matcher, status_code=200)
    matcher = re.compile(f"{DRS_URL}/ga4gh/drs/v1/objects/.+/download")
    tsv_string_data = """gene_id	length	effective_length	expected_count	TPM	FPKM
    ENSG00000000003.14	2000.22	1008.6	150.00	6.24	7.32
    """
    requests_mock.get(matcher, text=tsv_string_data, status_code=200)

    headers = {"Authorization": f"Bearer test", "Content-Type": "application/json"}
    with open("tests/genomic_ingest.json", "r") as f:
        data = json.load(f)
        for sample in data["analyses"]:
            response = htsget_ingest.link_genomic_data(sample)
            print(json.dumps(response, indent=4))
            assert len(response["errors"]) == 0
            assert "name" in response
            assert "sample" in response

    # bad sample:
    bad_s3_sample = {
        "program_id": "SYNTHETIC-2",
        "analysis_id": "bad_sample.cnv.vcf",
        "main": {
            "access_method": "s3://1000genomes/release/20130502/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz?public=true",
            "name": "bad_sample.cnv.vcf.gz"
        },
        "index": {
            "access_method": "s3://s3.us-east-1.amazonaws.com/1000genomes/release/20130502/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz.tbi?public=true",
            "name": "bad_sample.cnv.vcf.gz.tbi"
        },
        "metadata": {
            "analysis_type": "sequence_variation",
            "reference": "hg38"
        },
        "samples": [
            {
                "analysis_sample_id": "bad_sample",
                "submitter_sample_id": "SAMPLE_REGISTRATION_1"
            }
        ]
    }
    response = htsget_ingest.link_genomic_data(bad_s3_sample)
    print(json.dumps(response, indent=4))
    assert len(response["errors"]) == 1
