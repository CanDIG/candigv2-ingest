import argparse
import json
import os
import traceback
from collections import OrderedDict
from http import HTTPStatus

import requests
from requests.exceptions import ConnectionError
from flask import Blueprint, request

import auth
from ingest_result import IngestPermissionsException, IngestServerException, IngestResult

ingest_blueprint = Blueprint("ingest_donor", __name__)

def check_api_version(ingest_version, katsu_version):
    """
    Return True if the major and minor versions of the ingest and katsu are the same.
    The patch version of the ingest can be lower than katsu.

    Parameters:
    - ingest_version (str): in the format "major.minor.patch".
    - katsu_version (str): in the format "major.minor.patch".

    Returns:
    - bool
    """
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


def delete_data(katsu_server_url, data_location):
    """
    Delete all datasets.

    This function retrieves the list of program IDs from the 'Program.json' file
    and sends delete requests to delete each program along with all related data.
    """
    # Read the program IDs from the 'Program.json' file
    data = read_json(data_location + "Program.json")
    program_id_list = [item["program_id"] for item in data]

    # Delete datasets for each program ID
    for program_id in program_id_list:
        delete_url = f"{katsu_server_url}/katsu/v2/authorized/programs/{program_id}/"
        print(f"Deleting dataset {program_id}...")

        try:
            headers = auth.get_auth_header()
            headers["Content-Type"] = "application/json"
            # Send delete request
            response = requests.delete(delete_url, headers=headers)

            if response.status_code == requests.codes.NO_CONTENT:
                print(
                    f"DELETE OK 204! \nProgram {program_id} and all the related data have been deleted.\n"
                )
            else:
                print(
                    f"\nFAILED TO DELETE {program_id} \nRETURN STATUS CODE: {response.status_code} \nRETURN MESSAGE: {response.text}\n"
                )

        except requests.RequestException as e:
            print(f"\nERROR: Failed to delete {program_id}. \nException: {str(e)}\n")


def ingest_data(katsu_server_url, data_location):
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
            ("exposures", "Exposure.json"),
        ]
    )
    ingest_finished = False
    for api_name, file_name in file_mapping.items():
        ingest_str = f"/katsu/v2/ingest/{api_name}/"
        ingest_url = katsu_server_url + ingest_str

        print(f"Loading {file_name}...")
        payload = read_json(data_location + file_name)
        if payload is not None:
            headers = auth.get_auth_header()
            headers["Content-Type"] = "application/json"
            for elem in payload:
                response = requests.post(
                    ingest_url, headers=headers, data=json.dumps(elem)
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
        print("All files have been processed.")
    else:
        print("Aborting processing due to an error.")

def traverse_clinical_field(field: dict, ctype, parents, types, id_names, katsu_server_url, headers, errors,
                            ingested_ids):
    """
    Helper function for ingest_donor_with_clinical. Parses and ingests clinical fields from a DonorWithClinicalData
    object.
    Args:
        field: The (sub)field of a DonorWithClinicalData object, potentially nested
        ctype: The type of the field being ingested (e.g. "donors")
        parents: A dictionary mapping of the parents of this object, e.g.
            {   "donors": "DONOR_1",
                "primary_diagnoses": "submitter_primary_diagnosis_id",
            }
        types: A list of possible field types
        id_names: A mapping of field names to what their ID key is (e.g. {"donors": "submitter_donor_id"})
        errors: A list of strings containing the errors encountered so far
        ingested_ids: A list of IDs that have already been ingested (some fields in DonorWithClinical are duplicates)
    """
    no_ids = ["comorbidities", "exposures"] # fields that do not have an ID associated with them

    data = {}
    if ctype in id_names:
        id_key = id_names[ctype]
    else:
        id_key = "id"
    if ctype not in no_ids:
        field_id = field.pop(id_key)
        if field_id in ingested_ids:
            print(f"Skipping {field_id} (Already ingested).")
            return
        data[id_key] = field_id
        ingested_ids.append(field_id)

    attributes = list(field.keys())
    for attribute in attributes:
        if attribute not in types:
            data[attribute] = field.pop(attribute)

    for parent in parents:
        parent_key = id_names[parent]
        data[parent_key] = parents[parent]

    ingest_str = f"/katsu/v2/ingest/{ctype}/"
    ingest_url = katsu_server_url + ingest_str

    headers["refresh_token"] = auth.get_refresh_token(refresh_token=headers["refresh_token"])
    headers["Authorization"] = "Bearer %s" % auth.get_bearer_from_refresh(headers["refresh_token"])
    response = requests.post(
        ingest_url, headers=headers, data=json.dumps(data)
    )

    if response.status_code == HTTPStatus.CREATED:
        print(f"INGEST OK 201! \nRETURN MESSAGE: {response.text}\n")
    elif response.status_code == HTTPStatus.NOT_FOUND:
        message = f"ERROR 404: {ingest_url} was not found! Please check the URL."
        errors.append(message)
        return
    else:
        message = f"\nREQUEST STATUS CODE: {response.status_code} \nRETURN MESSAGE: {response.text}\n"
        print(message)
        errors.append(message)
        return

    if ctype not in no_ids:
        parents[ctype] = data[id_key]
    subfields = field.keys()
    for subfield in subfields:
        print(f"Loading {subfield} for {data[id_key]}...")
        for elem in field[subfield]:
            traverse_clinical_field(elem, subfield, parents, types, id_names, katsu_server_url, headers, errors,
                                    ingested_ids)
    if ctype not in no_ids:
        parents.pop(ctype)
    return errors

def ingest_donor_with_clinical(katsu_server_url, dataset, headers):
    """A single file ingest which loads an MOH donor_with_clinical_data object from JSON.
    JSON format:
    [
        {
            "submitter_donor_id": ...,
            "program_id": ...,
            ...
            primary_site: {...},
            primary_diagnoses: {...},
            ...
        }
        ...
    ]
    (Fully outlined in MOH Schema)
    """
    print("Beginning ingest")

    types = ["programs",
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
            "exposures"]
    id_names = {"programs": "program_id", "donors": "submitter_donor_id",
                "primary_diagnoses": "submitter_primary_diagnosis_id", "sample_registrations": "submitter_sample_id",
                "treatments": "submitter_treatment_id", "specimens": "submitter_specimen_id"}

    errors = []
    ingested_datasets = []
    for donor in dataset:
        program_id = donor.pop("program_id")
        if program_id not in ingested_datasets:
            headers["refresh_token"] = auth.get_refresh_token(refresh_token=headers["refresh_token"])
            headers["Authorization"] = "Bearer %s" % auth.get_bearer_from_refresh(headers["refresh_token"])
            request = requests.Request('POST', katsu_server_url + f"/katsu/v2/ingest/programs/", headers=headers,
                          data=json.dumps({"program_id": program_id}))
            if not auth.is_authed(request):
                return IngestPermissionsException(program_id)
            response = requests.Session().send(request.prepare())
            if response.status_code != HTTPStatus.CREATED:
                return IngestServerException([f"\nREQUEST STATUS CODE: {response.status_code}"
                                              f"\nRETURN MESSAGE: {response.text}\n"])
            ingested_datasets.append(program_id)
        parents = {"programs": program_id}
        print(f"Loading donor {donor['submitter_donor_id']}...")
        traverse_clinical_field(donor, "donors", parents, types, id_names, katsu_server_url, headers, errors, [])
    if errors:
        return IngestServerException(errors)
    else:
        return IngestResult(len(dataset))

def run_check(katsu_server_url, env_str, data_location, ingest_version):
    """
    Run a series of checks to ensure that the ingest is ready to run.
        - Check if the environment file exists
        - Check if the environment variable is set
        - Check if the Katsu server is running the correct version
        - Check header authentication
    """
    # Check if environment file exists
    if os.path.exists(env_str):
        print("PASS: The environment file exists.")
    else:
        print("ERROR ENV CHECK: The environment file does not exist.")

    # Check if environment variable is set
    if data_location:
        print("PASS: Data location is set.")
    else:
        print("ERROR LOCATION CHECK: data location is not set.")

    # check authorization
    try:
        headers = auth.get_auth_header()
        print("PASS: Auth header is ok.")
    except Exception as e:
        print(f"ERROR AUTH CHECK: {e}")
        exit()

    # check if Katsu server is running correct version
    version_check_url = katsu_server_url + "/v2/version_check"
    try:
        response = requests.get(version_check_url, headers=headers)
        if response.status_code == HTTPStatus.OK:
            katsu_version = response.json()["version"]
            if check_api_version(
                ingest_version=ingest_version, katsu_version=katsu_version
            ):
                print(f"PASS: Katsu server is running on a compatible version.")
            else:
                print(
                    f"ERROR: Katsu server is running on {katsu_version}. Required version {ingest_version} or greater."
                )
        else:
            print(f"ERROR VERSION CHECK {response.status_code}: {response.text}")
    except ConnectionError as e:
        print(f"ERROR VERSION CHECK: {e}")
        return

@ingest_blueprint.route('/ingest_donor', methods=["POST"])
def ingest_donor_endpoint():
    katsu_server_url = os.environ.get("CANDIG_URL")
    dataset = request.json
    headers = {}
    try:
        headers["Authorization"] = "Bearer %s" % auth.get_bearer_from_refresh(request.headers["refresh_token"])
    except Exception as e:
        if "Invalid refresh token" in str(e):
            return "Refresh token invalid or unauthorized", 403
    headers["refresh_token"] = request.headers["refresh_token"]
    headers["Content-Type"] = "application/json"
    response = ingest_donor_with_clinical(katsu_server_url, dataset, headers)
    if type(response) == IngestResult:
        return "Ingested %d donors.<br/>" % response.value, 200
    elif type(response) == IngestPermissionsException:
        return "Error: You are not authorized to write to program <br/>." % response.value, 403
    elif type(response) == IngestServerException:
        error_string = '<br/>'.join(response.value)
        return "Ingest encountered the following errors: <br/>%s" % error_string, 500
    return 500

def main():
    # check if os.environ.get("CANDIG_URL") is set
    if os.environ.get("CANDIG_URL") is None:
        print("ERROR: ENV is not set. Did you forget to run 'source env.sh'?")
        exit()
    katsu_server_url = os.environ.get("CANDIG_URL")
    headers = "GET_AUTH_HEADER"
    data_location = os.environ.get("CLINICAL_DATA_LOCATION")

    env_str = "env.sh"
    ingest_version = "2.1.0"

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-choice",
        type=int,
        choices=range(1, 4),
        help="Select an option: 1=Run check, 2=Ingest data, 3=Delete a dataset",
    )
    args = parser.parse_args()

    if args.choice is not None:
        choice = args.choice
    else:
        print("Select an option:")
        print("1. Run check")
        print("2. Ingest data")
        print("3. Clean data")
        print("4. Ingest DonorWithClincalData")
        print("5. Exit")
        choice = int(input("Enter your choice [1-5]: "))

    if choice == 1:
        run_check(
            katsu_server_url=katsu_server_url,
            env_str=env_str,
            data_location=data_location,
            ingest_version=ingest_version,
        )
    elif choice == 2:
        ingest_data(
            katsu_server_url=katsu_server_url,
            data_location=data_location,
        )
    elif choice == 3:
        response = input("Are you sure you want to delete? (yes/no): ")
        if response == "yes":
            delete_data(
                katsu_server_url=katsu_server_url,
                data_location=data_location,
            )
        else:
            print("Delete cancelled")
            exit()
    elif choice == 4:
        dataset = read_json(data_location)
        ingest_donor_with_clinical(katsu_server_url, dataset, headers)
    elif choice == 5:
        exit()
    else:
        print("Invalid option. Please try again.")


if __name__ == "__main__":
    main()
