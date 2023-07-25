import argparse
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
        delete_url = f"{katsu_server_url}/v2/authorized/programs/{program_id}/"

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
    def check_ingest_status(api_name, headers):
        """
        Helper function to check discovery endpoint
        """
        ingest_str = f"/v2/discovery/{api_name}"
        ingest_url = katsu_server_url + ingest_str
        check_response = requests.get(ingest_url, headers=headers, timeout=10)
        return check_response

    file_mapping = OrderedDict([
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
    ])
    
    ingest_finished = True

    for api_name, file_name in file_mapping.items():
        headers = auth.get_auth_header()
        headers["Content-Type"] = "application/json"
        ingest_str = f"/v2/ingest/{api_name}"
        ingest_url = katsu_server_url + ingest_str

        print(f"Loading {file_name}...")
        payload = read_json(data_location + file_name)
        if payload is None:
            print(f"ERROR: Unable to read {file_name}.")
            ingest_finished = False
            break

        try:
            response = requests.post(
                ingest_url, 
                headers=headers, 
                data=json.dumps(payload), 
                timeout=1000
            )
            response.raise_for_status()
            if response.status_code == HTTPStatus.CREATED:
                print(f"INGEST OK 201! \nRETURN MESSAGE: {response.text}\n")
            else:
                print(
                    f"ERROR: Ingest failed with status code {response.status_code}. \nRETURN MESSAGE: {response.text}\n"
                )
                ingest_finished = False
                break
        except requests.exceptions.Timeout:
            check_response = check_ingest_status(api_name, headers)
            if any(len(value) == 0 for value in json.loads(check_response.text).values()):
                print(f"ERROR: Ingest did not finish in time. You can try one of the following: increase timeout, restart katsu, make smaller request, or use katsu fixtures")
                ingest_finished = False
                break
            else:
                print(f"INGEST OK with content {check_response.text}")
        except requests.exceptions.RequestException as e:
            print("An error occurred:", e)
            print(
                f"\nREQUEST STATUS CODE: {response.status_code} \nRETURN MESSAGE: {response.text}\n"
            )
            ingest_finished = False
            break

    if ingest_finished:
        print("All files have been processed.")
    else:
        print("Aborting processing due to an error.")


def run_check(env_str, data_location):
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
    katsu_server_url = os.environ.get("CANDIG_URL") + "/katsu"
    data_location = os.environ.get("CLINICAL_DATA_LOCATION")

    env_str = "env.sh"

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
        print("3. Delete data")
        print("4. Exit")
        choice = int(input("Enter your choice [1-4]: "))

    if choice == 1:
        run_check(
            env_str=env_str,
            data_location=data_location,
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
        exit()
    else:
        print("Invalid option. Please try again.")


if __name__ == "__main__":
    main()
