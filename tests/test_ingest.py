import pytest
import json

import katsu_ingest

class TestFlattening:
    @pytest.fixture(autouse=True)
    def _set_fields(self):
        with open("single_ingest.json", "r") as f:
            data = json.load(f)
        self.fields = katsu_ingest.flatten_donor_with_clinical(data)

    def test_program(self):
        assert self.fields["programs"][0]["program_id"] == "SYNTHETIC-2"

    def test_donor(self):
        assert len(self.fields["donors"]) == 10
        assert self.fields["donors"][0]["program_id"] == "SYNTHETIC-2"

    def test_sample(self):
        sample_registrations = self.fields["sample_registrations"]
        for registration in sample_registrations:
            if registration["submitter_sample_id"] == "SAMPLE_REGISTRATION_25":
                assert registration["submitter_specimen_id"] == "SPECIMEN_19"
                assert registration["program_id"] == "SYNTHETIC-2"
                assert registration["submitter_donor_id"] == "DONOR_7"
                return None
        assert False # We didn't even find the relevant sample

    def test_followup(self):
        followups = self.fields["followups"]
        for followup in followups:
            if followup["submitter_follow_up_id"] == "FOLLOW_UP_1":
                assert followup["submitter_treatment_id"] == "TREATMENT_1"
                assert ("submitter_primary_diagnosis_id" not in followup) or \
                       (not followup["submitter_primary_diagnosis_id"] )


    def test_biomarker(self):
        biomarker_count = len(self.fields["biomarkers"])
        assert biomarker_count == 12

