import argparse
import json
import os
import sys
import traceback
from collections import OrderedDict
from http import HTTPStatus

import requests
import jsonschema

import auth
from ingest_result import (IngestPermissionsException, IngestServerException, IngestCohortException,
                           IngestResult, IngestValidationException)

sys.path.append('clinical_ETL_code')
from clinical_ETL_code import validate_coverage

def update_headers(headers):
    """
    For new auth model
    refresh_token = headers["refresh_token"]
    bearer = auth.get_bearer_from_refresh(refresh_token)
    new_refresh = auth.get_refresh_token(refresh_token=refresh_token)
    headers["refresh_token"] = new_refresh
    headers["Authorization"] = f"Bearer {bearer}"
    """
    pass
    
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
        print("All files have been processed.")
    else:
        print("Aborting processing due to an error.")

def ingest_fields(fields, katsu_server_url, headers):
    errors = []
    name_mappings = {"radiation": "radiations", "surgery": "surgeries", "followups": "follow_ups"}
    for type in fields:
        if type in name_mappings:
            name = name_mappings[type]
        else:
            name = type
        ingest_str = f"/katsu/v2/ingest/{name}/"
        ingest_url = katsu_server_url + ingest_str

        update_headers(headers)
        response = requests.post(
            ingest_url, headers=headers, data=json.dumps(fields[type])
        )

        if response.status_code == HTTPStatus.CREATED:
            print(f"INGEST OK 201! \nRETURN MESSAGE: {response.text}\n")
        elif response.status_code == HTTPStatus.NOT_FOUND:
            message = f"ERROR 404: {ingest_url} was not found! Please check the URL."
            print(message)
            errors.append(response.text)
        else:
            message = f"\nREQUEST STATUS CODE: {response.status_code} \nRETURN MESSAGE: {response.text}\n"
            print(message)
            errors.append(response.text)
    return errors

def traverse_clinical_field(fields, field: dict, ctype, parents, types, ingested_ids):
    """
    Helper function for ingest_donor_with_clinical. Parses and ingests clinical fields from a DonorWithClinicalData
    object.
    Args:
        field: The (sub)field of a DonorWithClinicalData object, potentially nested
        ctype: The type of the field being ingested (e.g. "donors")
        parents: A list of tuple mappings of the parents of this object, e.g.
            [
                ("donors", "DONOR_1"),
                ("primary_diagnoses", "PRIMARY_DIAGNOSIS_1")
            ]
        types: A list of possible field types
        id_names: A mapping of field names to what their ID key is (e.g. {"donors": "submitter_donor_id"})
        errors: A list of strings containing the errors encountered so far
        ingested_ids: A list of IDs that have already been ingested (some fields in DonorWithClinical are duplicates)
    """

    id_names = {"programs": "program_id", "donors": "submitter_donor_id",
                "primary_diagnoses": "submitter_primary_diagnosis_id", "sample_registrations": "submitter_sample_id",
                "treatments": "submitter_treatment_id", "specimens": "submitter_specimen_id",
                "followups": "submitter_follow_up_id"}

    data = {}
    if ctype in id_names:
        id_key = id_names[ctype]
    else:
        id_key = None
    if id_key:
        try:
            field_id = field.pop(id_key)
        except KeyError:
            raise ValueError(f"Missing required foreign key: {id_key} for {ctype} under {parents[-1][1]}")
        if field_id in ingested_ids:
            print(f"Skipping {field_id} (Already ingested).")
            return
        data[id_key] = field_id
        ingested_ids.append(field_id)

    attributes = list(field.keys())
    for attribute in attributes:
        if attribute not in types:
            data[attribute] = field.pop(attribute)

    if len(parents) >= 2: # Program & donor have been added (must be the first 2 fields)
        foreign_keys = [parents[0], parents[1]]
        if len(parents) > 2:
            foreign_keys.append(parents[-1])
    else:
        foreign_keys = [parents[0]] # Just program
    for parent in foreign_keys:
        parent_key = id_names[parent[0]]
        data[parent_key] = parent[1]

    fields[ctype].append(data)

    if id_key:
        parents.append((ctype, data[id_key]))
    subfields = field.keys()
    for subfield in subfields:
        if id_key:
            print(f"Loading {subfield} for {data[id_key]}...")
        else:
            print(f"Loading {subfield}...")
        if type(field[subfield]) == list:
            for elem in field[subfield]:
                traverse_clinical_field(fields, elem, subfield, parents, types, ingested_ids)
        elif type(field[subfield]) == dict:
            traverse_clinical_field(fields, field[subfield], subfield, parents, types, ingested_ids)
    if id_key:
        parents.pop(-1)

def ingest_donor_with_clinical(katsu_server_url, dataset, headers):
    """A single file ingest which validates and loads an MOH donor_with_clinical_data object from JSON.
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
    print("Validating input")
    try:
        result = validate_coverage.validate_coverage(dataset, "katsu_manifest.yml")
    except jsonschema.exceptions.ValidationError as e:
        return IngestValidationException("ETL JSONSCHEMA VALIDATION FAILED. Run through clinical ETL validation to "
                                        "repair these issues.", [str(e)])
    if len(result) != 0:
        return IngestValidationException("ETL VALIDATION FAILED. Run through clinical ETL validation to "
                                        "repair these issues.", [str(line) for line in result])
    print("Validation success.")

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
            "followups",
            "biomarkers",
            "comorbidities",
            "exposures"]
    fields = {type: [] for type in types}

    ingested_datasets = []
    for donor in dataset:
        program_id = donor.pop("program_id")
        if program_id not in ingested_datasets:
            update_headers(headers)
            program_endpoint = "/katsu/v2/ingest/programs/"
            request = requests.Request('POST', katsu_server_url + program_endpoint, headers=headers,
                          data=json.dumps([{"program_id": program_id}]))
            if not auth.is_authed(request):
                return IngestPermissionsException(f"Not authorized to write to {program_id}")
            response = requests.Session().send(request.prepare())
            if response.status_code != HTTPStatus.CREATED:
                    if 'unique' in response.text:
                        return IngestCohortException(f"Program {program_id} has already been ingested into Katsu. "
                                                   "Please delete and try again.")
                    else:
                        return IngestServerException([f"\nREQUEST STATUS CODE: {response.status_code}"
                                                      f"\nRETURN MESSAGE: {response.text}\n"])
            ingested_datasets.append(program_id)
        parents = [("programs", program_id)]
        print(f"Loading donor {donor['submitter_donor_id']}...")
        try:
            traverse_clinical_field(fields, donor, "donors", parents, types, [])
        except Exception as e:
            print(traceback.format_exc())
            return IngestServerException(str(e))
    fields.pop("programs")
    errors = ingest_fields(fields, katsu_server_url, headers)
    if errors:
        return IngestServerException(errors)
    else:
        return IngestResult(len(dataset))

def run_check(katsu_server_url, env_str, data_location):
    """
    Run a series of checks to ensure that the ingest is ready to run.
        - Check if the environment file exists
        - Check if the environment variable is set
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

def main():
    # check if os.environ.get("CANDIG_URL") is set
    if os.environ.get("CANDIG_URL") is None:
        print("ERROR: ENV is not set. Did you forget to run 'source env.sh'?")
        exit()
    katsu_server_url = os.environ.get("CANDIG_URL")
    headers = auth.get_auth_header()
    data_location = os.environ.get("CLINICAL_DATA_LOCATION")
    if not data_location:
        print("ERROR: Data location is not assigned. Please set the environment variable CLINICAL_DATA_LOCATION.")
        exit()

    env_str = "env.sh"

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-choice",
        type=int,
        choices=range(1, 4),
        help="Select an option: 1=Run check, 2=Ingest data, 3=Delete a dataset, 4=Ingest DonorWithClinicalData",
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
            data_location=data_location
        )
    elif choice == 2:
        if not data_location.endswith('/'):
            data_location += '/'
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
        dataset = read_json(data_location)["donors"]
        headers["Content-Type"] = "application/json"
        result = ingest_donor_with_clinical(katsu_server_url, dataset, headers)
        print(result.value)
        if type(result) == IngestValidationException:
            [print(error) for error in result.validation_errors]
    elif choice == 5:
        exit()
    else:
        print("Invalid option. Please try again.")


if __name__ == "__main__":
    main()
