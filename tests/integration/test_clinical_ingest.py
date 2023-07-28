import os
import requests
import pytest
import warnings
import json

import katsu_ingest
from auth import get_auth_header

KATSU_URL = os.environ.get("CANDIG_URL")

@pytest.fixture
def headers():
    return get_auth_header()

@pytest.fixture(autouse=True, scope="module")
def setup_ingest():
    headers = get_auth_header()
    if os.getenv("PROD_ENVIRONMENT") == "TRUE":
        print("PRODUCTION ENVIRONMENT DETECTED - ABORTING TESTS\n"
              "Ingest tests require the deletion of some datasets which can be dangerous in a production environment. "
              "Please run them on a development environment instead.")
        warnings.warn("Production environment detected - ingest tests will not run")
        exit()
    #data_location = "https://raw.githubusercontent.com/CanDIG/katsu/develop/chord_metadata_service/mohpackets/data/small_dataset/synthetic_data/"
    requests.delete(KATSU_URL + "/katsu/v2/authorized/programs/SYNTHETIC-2/", headers=headers)
    with open("single_ingest.json", "r") as f:
        dataset = json.load(f)
    katsu_ingest.ingest_donor_with_clinical(KATSU_URL, dataset, headers)

def check_exists(headers, endpoint, number=-1):
    response = requests.get(KATSU_URL + endpoint,
                            headers=headers)
    if (number == -1):
        assert response.json()["results"]
    else:
        assert len(response.json()["results"]) == number

class TestClinicalIngest:
    @pytest.fixture(autouse=True)
    def _set_admin_headers(self, headers):
        self.headers = headers

    def test_programs(self):
        check_exists(self.headers, "/katsu/v2/authorized/programs/?program_id=%s" % "SYNTHETIC-2")
    def test_donors(self):
        donor_id = 'DONOR_7'
        check_exists(self.headers, "/katsu/v2/authorized/donors/?submitter_donor_id=%s" % donor_id)
        check_exists(self.headers, "/katsu/v2/authorized/donors/", 10)
    def test_comorbidities(self):
        check_exists(self.headers, "/katsu/v2/authorized/comorbidities/", 14)
    def test_exposures(self):
        check_exists(self.headers, "/katsu/v2/authorized/exposures/", 8)
    def test_specimens(self):
        s_id = "SPECIMEN_19"
        check_exists(self.headers, "/katsu/v2/authorized/specimens/?specimen_id=%s" % s_id)
        check_exists(self.headers, "/katsu/v2/authorized/specimens/", 22)
    def test_biomarkers(self):
        check_exists(self.headers, "/katsu/v2/authorized/biomarkers/",  12)
    def test_follow_ups(self):
        f_id = "FOLLOW_UP_25"
        check_exists(self.headers, "/katsu/v2/authorized/follow_ups/?submitter_follow_up_id=%s" % f_id)
        check_exists(self.headers, "/katsu/v2/authorized/follow_ups/", 28)
    def test_chemotherapies(self):
        check_exists(self.headers, "/katsu/v2/authorized/chemotherapies/", 7)
    def test_radiations(self):
        check_exists(self.headers, "/katsu/v2/authorized/radiations/", 5)
    def test_surgeries(self):
        check_exists(self.headers, "/katsu/v2/authorized/surgeries/", 5)
    def test_immunotherapies(self):
        check_exists(self.headers, "/katsu/v2/authorized/immunotherapies/", 7)
    def test_treatments(self):
        treatment_id = "TREATMENT_1"
        check_exists(self.headers, "/katsu/v2/authorized/treatments/?submitter_treatment_id=%s" % treatment_id)
        check_exists(self.headers, "/katsu/v2/authorized/treatments/", 22)
    def test_hormone(self):
        check_exists(self.headers, "/katsu/v2/authorized/hormone_therapies/", 7)
    def test_sample(self):
        sample_id = "SAMPLE_REGISTRATION_1"
        check_exists(self.headers, "/katsu/v2/authorized/sample_registrations/?submitter_sample_id=%s" % sample_id)
        check_exists(self.headers, "/katsu/v2/authorized/sample_registrations/", 28)
    def test_diagnoses(self):
        diag_id = "PRIMARY_DIAGNOSIS_1"
        check_exists(self.headers,
                     "/katsu/v2/authorized/primary_diagnoses/?submitter_primary_diagnosis_id=%s" % diag_id)
        check_exists(self.headers, "/katsu/v2/authorized/primary_diagnoses/", 16)