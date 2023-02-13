import json
import os
from collections import OrderedDict
from http import HTTPStatus

import requests
from requests.exceptions import ConnectionError

import auth


def check_api_version(ingest_version, katsu_version):
    ingest_version_parts = ingest_version.split(".")
    ingest_major, ingest_minor, ingest_patch = map(int, ingest_version_parts)
    katsu_version_parts = katsu_version.split(".")
    katsu_major, katsu_minor, katsu_patch = map(int, katsu_version_parts)

    if ingest_major == katsu_major:
        if ingest_minor == katsu_minor:
            if ingest_patch <= katsu_patch:
                return True
    return False


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


def clean_data(katsu_server_url, headers):
    """
    Sends a DELETE request to the Katsu server to delete all data.
    """
    response = input("Are you sure you want to delete the database? (yes/no): ")

    if response == "yes":
        delete_url = "/api/v1/delete/all"
        url = katsu_server_url + delete_url

        # if headers == "GET_AUTH_HEADER":
        #     headers = auth.get_auth_header()
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


def ingest_data(katsu_server_url, location_str, synthetic_data_url, headers):
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
    # get local data from environment or use synthetic data
    moh_data_location = os.environ.get(location_str) or synthetic_data_url
    ingest_finished = False
    for api_name, file_name in file_mapping.items():
        ingest_str = f"/api/v1/ingest/{api_name}"
        ingest_url = katsu_server_url + ingest_str

        print(f"Loading {file_name}...")
        payload = read_json(moh_data_location + file_name)
        if payload is not None:
            # if headers == "GET_AUTH_HEADER":
            #     headers = auth.get_auth_header()
            response = requests.post(
                ingest_url, headers=headers, data=json.dumps(payload)
            )

            if response.status_code == HTTPStatus.CREATED:
                print(f"INGEST OK 201! \nRETURN MESSAGE: {response.text}\n")
            elif response.status_code == HTTPStatus.NOT_FOUND:
                print(f"ERROR 404: {ingest_url} was not found! Please check the URL.")
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


def run_check(katsu_server_url, env_str, location_str, headers):
    # Check if environment file exists
    if os.path.exists(env_str):
        print("PASS: The environment file exists.")
    else:
        print("ERROR: The environment file does not exist.")

    # Check if environment variable is set
    if os.environ.get(location_str):
        print("PASS: MOH_DATA_LOCATION environment variable is set.")
    else:
        print(
            "WARNING: MOH_DATA_LOCATION environment variable is not set. Ignore this if using synthetic data."
        )

    # check if Katsu server is running
    health_check_url = katsu_server_url + "/api/v1/health_check"
    try:
        response = requests.get(health_check_url)
        if response.status_code == HTTPStatus.OK:
            # check if response.text > v0.1.0
            katsu_version = response.json()["version"]
            ingest_version = "0.9.0"
            if check_api_version(
                ingest_version=ingest_version, katsu_version=katsu_version
            ):
                print(f"PASS: Katsu server is running.")
            else:
                print(
                    f"ERROR: Katsu server is running on {katsu_version}. Required version {ingest_version} or greater."
                )
        else:
            print(f"ERROR {response.status_code}: {response.text}")
    except ConnectionError as e:
        print(f"ERROR: {e}")
        return

    # check authorization
    if headers == "GET_AUTH_HEADER":
        try:
            headers = auth.get_auth_header()
            print("PASS: Auth header is set.")
        except Exception as e:
            print(f"ERROR: {e}")


def main():
    print("Select an option:")
    print("1. Run check")
    print("2. Ingest data")
    print("3. Clean data")
    print("4. Exit")

    # NOTE: FOR DEVELOPMENT ONLY: if you have a local Katsu running and
    # doesn't want to use auth stack, uncomment the lines below and
    # comment out the lines after that
    katsu_server_url = "http://127.0.0.1:8000"
    # headers = {"Content-Type": "application/json"}
    # katsu_server_url = os.environ.get("CANDIG_URL") + "/katsu"
    headers = "GET_AUTH_HEADER"
    env_str = "env.sh"
    location_str = "MOH_DATA_LOCATION"
    synthetic_data_url = "https://raw.githubusercontent.com/CanDIG/katsu/sonchau/moh_part_22/chord_metadata_service/mohpackets/data/small_dataset/synthetic_data/"

    choice = int(input("Enter your choice [1-3]: "))

    if choice == 1:
        run_check(
            katsu_server_url=katsu_server_url,
            env_str=env_str,
            location_str=location_str,
            headers=headers,
        )
    elif choice == 2:
        ingest_data(
            katsu_server_url=katsu_server_url,
            location_str=location_str,
            synthetic_data_url=synthetic_data_url,
            headers=headers,
        )
    elif choice == 3:
        clean_data(katsu_server_url, headers)
    elif choice == 4:
        exit()
    else:
        print("Invalid option. Please try again.")


if __name__ == "__main__":
    main()
