import os
import requests
import pytest

import katsu_ingest
from auth import get_auth_header

KATSU_URL = os.environ.get("CANDIG_URL")

@pytest.fixture
def headers_admin():
    return get_auth_header()

@pytest.fixture
def headers_non_admin():
    return get_auth_header(admin=False)

@pytest.fixture(autouse=True)
def setup_ingest(headers_admin):
    data_location = "https://raw.githubusercontent.com/CanDIG/katsu/develop/chord_metadata_service/mohpackets/data/small_dataset/synthetic_data/"
    katsu_ingest.clean_data(KATSU_URL, headers_admin)
    katsu_ingest.ingest_data(KATSU_URL, data_location, headers_admin)

def check_exists(headers, endpoint, number=-1):
    response = requests.get("%s%s" % (KATSU_URL, endpoint),
                            headers=headers)
    if (number == -1):
        assert response.json()["results"]
    else:
        assert len(response.json()["results"]) == number

def check_not_exists(headers, endpoint):
    response = requests.get("%s%s" % (KATSU_URL, endpoint),
                            headers=headers)
    assert not response.json()["results"]

class TestClinicalIngest:
    @pytest.fixture(autouse=True)
    def _set_admin_headers(self, headers_admin):
        self.headers_admin = headers_admin
    @pytest.fixture(autouse=True)
    def _set_headers(self, headers_non_admin):
        self.headers = headers_non_admin

    def test_programs(self):
        program_1 = 'SYNTHETIC-1'
        program_2 = 'SYNTHETIC-2'
        check_exists(self.headers, "/katsu/v2/authorized/programs/?program_id=%s" % program_1)
        check_exists(self.headers_admin, "/katsu/v2/authorized/programs/?program_id=%s" % program_2)
    def test_donors(self):
        donor_id_1 = 'DONOR_7'
        donor_id_2 = 'DONOR_1'
        check_exists(self.headers_admin, "/katsu/v2/authorized/donors/?submitter_donor_id=%s" % donor_id_1)
        check_exists(self.headers, "/katsu/v2/authorized/donors/?submitter_donor_id=%s" % donor_id_2)
    def test_comorbidities(self):
        c_type = "C64.9"
        check_exists(self.headers_admin, "/katsu/v2/authorized/comorbidities/?comorbidity_type_code=%s" % c_type)
    def test_exposures(self):
        years_smoked = "104.0"
        check_exists(self.headers_admin, "/katsu/v2/authorized/comorbidities/?pack_years_smoked=%s" % years_smoked)
    def test_specimens(self):
        s_id = "SPECIMEN_19"
        check_exists(self.headers_admin, "/katsu/v2/authorized/specimens/?specimen_id=%s" % s_id)
        check_exists(self.headers, "/katsu/v2/authorized/specimens/?specimen_id=%s" % s_id)
    def test_biomarkers(self):
        s_id = "SPECIMEN_1"
        check_exists(self.headers, "/katsu/v2/authorized/biomarkers/?submitter_specimen_id=%s" % s_id)
        check_not_exists(self.headers_admin, "/katsu/v2/authorized/biomarkers/?submitter_specimen_id=%s" % s_id)
    def test_follow_ups(self):
        f_id = "FOLLOW_UP_25"
        check_exists(self.headers_admin, "/katsu/v2/authorized/follow_ups/?submitter_follow_up_id=%s" % f_id)
        check_exists(self.headers, "/katsu/v2/authorized/follow_ups/?submitter_follow_up_id", 24)
    def test_chemotherapies(self):
        donor_id = "DONOR_1"
        check_exists(self.headers, "/katsu/v2/authorized/chemotherapies/?submitter_donor_id=%s" % donor_id, 7)
        check_not_exists(self.headers_admin, "/katsu/v2/authorized/chemotherapies/?submitter_donor_id=%s" % donor_id)
    def test_radiations(self):
        check_exists(self.headers, "/katsu/v2/authorized/radiations/", 5)
        check_not_exists(self.headers_admin, "/katsu/v2/authorized/radiations/")
    def test_surgeries(self):
        check_exists(self.headers, "/katsu/v2/authorized/surgeries/", 1)
        check_exists(self.headers_admin, "/katsu/v2/authorized/surgeries/", 4)
    def test_immunotherapies(self):
        check_exists(self.headers, "/katsu/v2/authorized/immunotherapies/", 7)
        check_not_exists(self.headers_admin, "/katsu/v2/authorized/immunotherapies/")
    def test_treatments(self):
        check_exists(self.headers, "/katsu/v2/authorized/treatments/", 18)
        check_exists(self.headers_admin, "/katsu/v2/authorized/treatments/", 4)
    def test_hormone(self):
        check_exists(self.headers, "/katsu/v2/authorized/hormone_therapies/", 7)
        check_not_exists(self.headers_admin, "/katsu/v2/authorized/hormone_therapies/")
    def test_sample(self):
        check_exists(self.headers, "/katsu/v2/authorized/sample_registrations/", 24)
        check_exists(self.headers_admin, "/katsu/v2/authorized/sample_registrations/", 4)
    def test_diagnoses(self):
        check_exists(self.headers, "/katsu/v2/authorized/primary_diagnoses/", 12)
        check_exists(self.headers_admin, "/katsu/v2/authorized/primary_diagnoses/", 4)




