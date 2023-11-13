import pytest
import json

import katsu_ingest

def test_prepare_clinical_ingest():
    with open("tests/single_ingest.json", "r") as f:
        data = json.load(f)
        result = katsu_ingest.prepare_clinical_data_for_ingest(data)
        print(json.dumps(result, indent=4))
        assert len(result) == 2
        assert len(result["SYNTHETIC-2"]["schemas"]["immunotherapies"]) == 2


