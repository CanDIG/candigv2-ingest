import json
from collections import OrderedDict
from http import HTTPStatus

import requests

# NOTE: we need to ingest in the following order since each model has a
# foreign key dependency on the previous model
model_names = [
    "programs",
    "donors",
    "primary_diagnoses",
    "specimens",
    "sample_registrations",
    "treatments",
    "chemotherapies",
    "hormone_therapies",
    "radiations",
    "immunotherapies",
    "surgeries",
    "follow_ups",
    "biomarkers",
    "comorbidities",
]
# make a dict with model_name and file_name
name_dict = {
    "programs": "Program.json",
    "donors": "Donor.json",
    "primary_diagnoses": "PrimaryDiagnosis.json",
    "specimens": "Specimen.json",
    "sample_registrations": "SampleRegistration.json",
    "treatments": "Treatment.json",
    "chemotherapies": "Chemotherapy.json",
    "hormone_therapies": "HormoneTherapy.json",
    "radiations": "Radiation.json",
    "immunotherapies": "Immunotherapy.json",
    "surgeries": "Surgery.json",
    "follow_ups": "FollowUp.json",
    "biomarkers": "Biomarker.json",
    "comorbidities": "Comorbidity.json",
}
# make name_dict an ordered dict
ordered_name_dict = OrderedDict(
    [
        ("programs", "Program.json"),
        ("donors", "Donor.json"),
        ("primary_diagnoses", "PrimaryDiagnosis.json"),
        ("specimens", "Specimen.json"),
        ("sample_registrations", "SampleRegistration.json"),
        ("treatments", "Treatment.json"),
        ("chemotherapies", "Chemotherapy.json"),
        ("hormone_therapies", "HormoneTherapy.json"),
        ("radiations", "Radiation.json"),
        ("immunotherapies", "Immunotherapy.json"),
        ("surgeries", "Surgery.json"),
        ("follow_ups", "FollowUp.json"),
        ("biomarkers", "Biomarker.json"),
        ("comorbidities", "Comorbidity.json"),
    ]
)
# katsu_server_url = "http://docker.localhost:5080/katsu"
katsu_server_url = "http://127.0.0.1:8000"

# Load the JSON data from the ordered_name_dict
for api_name, file_name in ordered_name_dict.items():
    with open(f"data/{file_name}", "r") as f:
        payload = json.load(f)

    # Make the POST request
    post_url = f"/api/v1/ingest/{api_name}"
    url = katsu_server_url + post_url
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, data=json.dumps(payload))

    if response.status_code == HTTPStatus.CREATED:
        print(
            f"\nREQUEST STATUS CODE: {response.status_code} \nRETURN MESSAGE: {response.text}\n"
        )
    else:
        print(
            f"\nREQUEST STATUS CODE: {response.status_code} \nRETURN MESSAGE: {response.text}\n"
        )
        break
