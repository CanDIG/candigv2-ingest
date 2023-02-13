import json
import os
from collections import OrderedDict
from http import HTTPStatus

import requests

import auth


def read_json(file_path):
    """Read data from either a URL or a local file in JSON format.

    Parameters
    ----------
    file_path : str
        The URL or the local file path from which the data should be read.

    Returns
    -------
    data : dict or None
        A dictionary containing the data read from the URL or local file,
        or `None` if the data could not be retrieved or the file does not exist.

    Examples
    --------
    >>> read_json("https://example.com/remote_file.json")
    >>> read_json("data/local_file.json")
    """

    if file_path.startswith("http"):
        try:
            response = requests.get(file_path)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            print("Failed to retrieve data. Error:", e)
            return None
    else:
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                return data
        except FileNotFoundError as e:
            print("File not found. Error:", e)
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
    moh_data_location = os.environ.get("MOH_DATA_LOCATION") or synthetic_data_url
    ingest_finished = False
    for api_name, file_name in file_mapping.items():
        post_url = f"/api/v1/ingest/{api_name}"
        url = katsu_server_url + post_url
        # headers = auth.get_auth_header()
        headers = {"Content-Type": "application/json"}

        print(f"Loading {file_name}...")
        payload = read_json(moh_data_location + file_name)
        if payload is not None:
            response = requests.post(url, headers=headers, data=json.dumps(payload))

            if response.status_code == HTTPStatus.CREATED:
                print(f"INGEST OK 201! \nRETURN MESSAGE: {response.text}\n")
            elif response.status_code == HTTPStatus.NOT_FOUND:
                print(f"ERROR 404: {url} was not found! Please check the URL.")
                break
            else:
                print(
                    f"\nREQUEST STATUS CODE: {response.status_code} \nRETURN MESSAGE: {response.text}\n"
                )
                break
    else:
        ingest_finished = True

    if ingest_finished:
        print("All files have been processed successfully.")
    else:
        print("Aborting processing due to an error.")


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
