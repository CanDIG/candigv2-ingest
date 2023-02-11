import json
from collections import OrderedDict
from http import HTTPStatus

import requests

import auth


def read_json_from_url(file_url):
    try:
        response = requests.get(file_url)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print("Failed to retrieve data. Error:", e)
        return None


def clean_data():
    """
    Sends a DELETE request to the Katsu server to delete all data.
    """
    response = input("Are you sure you want to delete the database? (yes/no): ")

    if response == "yes":
        katsu_server_url = "http://127.0.0.1:8000"
        delete_url = "/api/v1/delete/all"
        url = katsu_server_url + delete_url

        # headers = auth.get_auth_header()
        headers = {"Content-Type": "application/json"}

        res = requests.delete(url, headers=headers)
        if res.status_code == HTTPStatus.NO_CONTENT:
            print(f"Delete successful with status code {res.status_code}")
        else:
            print(
                f"Delete failed with status code {res.status_code} and message: {res.text}"
            )
    else:
        print("Delete cancelled")
        exit()


def ingest_data():
    """
    Send POST requests to the Katsu server to ingest data.
    """
    file_mapping = OrderedDict(
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
    synthetic_data_url = "https://raw.githubusercontent.com/CanDIG/katsu/sonchau/moh_part_22/chord_metadata_service/mohpackets/data/small_dataset/synthetic_data/"

    for api_name, file_name in file_mapping.items():
        post_url = f"/api/v1/ingest/{api_name}"
        url = katsu_server_url + post_url
        # headers = auth.get_auth_header()
        headers = {"Content-Type": "application/json"}

        print(f"Loading {file_name}...")
        payload = read_json_from_url(synthetic_data_url + file_name)
        if payload is None:
            break

        response = requests.post(url, headers=headers, data=json.dumps(payload))

        if response.status_code == HTTPStatus.CREATED:
            print(f"INGEST OK! \nRETURN MESSAGE: {response.text}\n")
        else:
            print(
                f"\nREQUEST STATUS CODE: {response.status_code} \nRETURN MESSAGE: {response.text}\n"
            )
            break


def main():
    print("Select an option:")
    print("1. Ingest data")
    print("2. Clean data")
    print("3. Exit")

    choice = int(input("Enter your choice [1-3]: "))

    if choice == 1:
        ingest_data()
    elif choice == 2:
        clean_data()
    elif choice == 3:
        exit()
    else:
        print("Invalid option. Please try again.")


if __name__ == "__main__":
    main()
