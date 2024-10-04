import argparse
import json
import os
import traceback
from http import HTTPStatus
import requests
import auth
from authx.auth import get_site_admin_token, create_service_token, is_action_allowed_for_program
from clinical_etl.mohschemav3 import MoHSchemaV3
from candigv2_logging.logging import initialize, CanDIGLogger

KATSU_URL = os.environ.get("KATSU_URL")

logger = CanDIGLogger(__file__)


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
            logger.error("Failed to retrieve data. Error:", e)
            return None
    else:
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                return data
        except FileNotFoundError as e:
            logger.error("File not found. Error:", e)
            return None


## This will be called by the daemon
def ingest_schemas(fields, batch_size=1000):
    result = {"errors": [], "results": []}

    # Use service token to authenticate this with katsu
    headers = {
        "X-Service-Token": create_service_token(),
        "Content-Type": "application/json"
    }

    for type in fields:
        if len(fields[type]) > 0:
            ingest_url = f"{KATSU_URL}/v3/ingest/{type}/"

            created_count = 0
            total_count = len(fields[type])

            data = fields[type]
            for i in range(0, len(data), batch_size):
                batch = data[i : i + batch_size]
                response = requests.post(
                    ingest_url, headers=headers, data=json.dumps(batch)
                )
                if response.status_code == HTTPStatus.CREATED:
                    created_count += len(batch)
                elif response.status_code == HTTPStatus.NOT_FOUND:
                    message = (
                        f"ERROR 404: {ingest_url} was not found! Please check the URL."
                    )
                    result["errors"].append(f"{type}: {message}")
                    break
                elif response.status_code == HTTPStatus.UNAUTHORIZED:
                    message = f"ERROR 401: You do not have permission to ingest {type}"
                    result["errors"].append(f"{type}: {message}")
                    break
                else:
                    try:
                        if "error" in response.json():
                            result["errors"].append(
                                f"{type}: {response.status_code} {response.json()['error']}"
                            )
                    except:
                        message = f"\nREQUEST STATUS CODE: {response.status_code} \nRETURN MESSAGE: {response.text}\n"
                        result["errors"].append(f"{type}: {message}")
                    if type == "programs" and "unique" in response.text:
                        # this is still okay to return 200:
                        return result, 200
            result["results"].append(
                f"Of {total_count} {type}, {created_count} were created"
            )
    return result, response.status_code


def traverse_clinical_field(fields, field: dict, ctype, parents, types, ingested_ids):
    """
    Helper function for prep_check_clinical_data. Parses and ingests clinical fields from a DonorWithClinicalData
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
        ingested_ids: A list of IDs that have already been ingested (some fields in DonorWithClinical are duplicates)
    """

    id_names = {
        "programs": "program_id",
        "donors": "submitter_donor_id",
        "primary_diagnoses": "submitter_primary_diagnosis_id",
        "sample_registrations": "submitter_sample_id",
        "treatments": "submitter_treatment_id",
        "specimens": "submitter_specimen_id",
        "followups": "submitter_follow_up_id",
    }

    data = {}
    if ctype in id_names:
        id_key = id_names[ctype]
    else:
        id_key = None
    if id_key:
        try:
            field_id = field.pop(id_key)
        except KeyError:
            raise ValueError(
                f"Missing required foreign key: {id_key} for {ctype} under {parents[-1][1]}"
            )
        if id_key not in ingested_ids:
            ingested_ids[id_key] = []
        if field_id in ingested_ids[id_key]:
            logger.info(f"Skipping {field_id} in {id_key} (Already ingested).")
            return
        data[id_key] = field_id
        ingested_ids[id_key].append(field_id)

    attributes = list(field.keys())
    for attribute in attributes:
        if attribute not in types:
            data[attribute] = field.pop(attribute)

    if (
        len(parents) >= 2
    ):  # Program & donor have been added (must be the first 2 fields)
        foreign_keys = [parents[0], parents[1]]
        if len(parents) > 2:
            foreign_keys.append(parents[-1])
    else:
        foreign_keys = [parents[0]]  # Just program
    for parent in foreign_keys:
        parent_key = id_names[parent[0]]
        data[parent_key] = parent[1]

    fields[ctype].append(data)

    if id_key:
        parents.append((ctype, data[id_key]))
    subfields = field.keys()
    for subfield in subfields:
        if type(field[subfield]) == list:
            for elem in field[subfield]:
                traverse_clinical_field(
                    fields, elem, subfield, parents, types, ingested_ids
                )
        elif type(field[subfield]) == dict:
            traverse_clinical_field(
                fields, field[subfield], subfield, parents, types, ingested_ids
            )
    if id_key:
        parents.pop(-1)


def prepare_clinical_data_for_ingest(ingest_json):
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
    schema = MoHSchemaV3(ingest_json["openapi_url"])

    types = ["programs"]
    types.extend(schema.validation_schema.keys())

    # split ingest by program_id:
    by_program = {}
    for donor in ingest_json["donors"]:
        if "program_id" not in donor:
            pass
        if donor["program_id"] not in by_program:
            by_program[donor["program_id"]] = {"donors": [], "errors": []}
        by_program[donor["program_id"]]["donors"].append(donor)

    for program_id in by_program.keys():
        errors = by_program[program_id]["errors"]
        logger.info(f"Validating input for program {program_id}")
        schema.validate_ingest_map(by_program[program_id])
        if len(schema.validation_warnings) > 0:
            logger.info("Validation returned warnings:")
            logger.info("\n".join(schema.validation_warnings))
        if len(schema.validation_errors) > 0:
            errors.append([str(line) for line in schema.validation_errors])
            continue
        logger.info("Validation success.")

        donors = by_program[program_id].pop("donors")
        fields = {type: [] for type in types}
        for donor in donors:
            parents = [("programs", program_id)]
            try:
                ingested_ids = {}
                traverse_clinical_field(
                    fields, donor, "donors", parents, types, ingested_ids
                )
            except Exception as e:
                logger.error(traceback.format_exc())
                errors.append(str(e))
        by_program[program_id]["schemas"] = fields
        by_program[program_id]["schemas"]["programs"] = [
            {"program_id": program_id, "metadata": schema.statistics.copy()}
        ]
    return by_program


def prep_check_clinical_data(ingest_json, token, batch_size):
    # check to see if we're running in an environment with an active katsu:
    # if we can get a response for the katsu schema url, use that.
    result = {}

    active_schema_url = f"{KATSU_URL}/static/schema.yml"
    try:
        response = requests.get(active_schema_url)
        if response.status_code == 200:
            logger.info(f"Validating against active katsu schema at {active_schema_url}")

            # compare this schema against the one listed in the ingest_json:
            response2 = requests.get(ingest_json["openapi_url"])
            if response2.status_code == 200:
                if response2.text != response.text:
                    result["warnings"] = [f"CanDIG is using a different schema version than the one listed in the clinical data file! Please compare your data against {os.getenv('CANDIG_URL')}/katsu/static/schema.yml."]

            ingest_json["openapi_url"] = active_schema_url
    except:
        pass

    schemas_to_ingest = prepare_clinical_data_for_ingest(ingest_json)
    result["errors"] = {}

    for program_id in schemas_to_ingest.keys():
        result["errors"][program_id] = []
        program = schemas_to_ingest[program_id]
        response, status_code = auth.get_program_in_opa(program_id, token)
        if status_code > 300:
            result["errors"][program_id].append({"not found": "No program authorization exists"})
        if not is_action_allowed_for_program(token, method="POST", path="/v3/ingest/programs/", program=program_id):
            result["errors"][program_id].append({"unauthorized": "user is not allowed to ingest to program"})
        if len(program["errors"]) > 0:
            result["errors"][program_id].extend(program["errors"])
        if len(result["errors"][program_id]) == 0:
            result["errors"].pop(program_id)

    # if any of the programs had errors, return:
    if len(result["errors"]) > 0:
        return result, 400
    return schemas_to_ingest, 200


def main():
    # check if os.environ.get("CANDIG_URL") is set
    global KATSU_URL
    if KATSU_URL is None:
        if os.getenv("CANDIG_URL") is None:
            print(
                "ERROR: $CANDIG_URL is not set. Did you forget to run 'source env.sh'?"
            )
            exit()
        KATSU_URL = f"{os.getenv('CANDIG_URL')}/katsu"

    token = get_site_admin_token()

    parser = argparse.ArgumentParser(
        description="A script that ingests clinical data into Katsu"
    )
    parser.add_argument("--input", help="Path to the clinical json file to ingest.")
    parser.add_argument("--batch_size", help="How many items for batch ingest.")
    args = parser.parse_args()

    data_location = args.input
    if not data_location:
        data_location = os.environ.get("CLINICAL_DATA_LOCATION")
        if not data_location:
            print(
                "ERROR: Could not find input data. Either --input is required or CLINICAL_DATA_LOCATION must be set."
            )
            exit()
    batch_size = 1000
    if args.batch_size:
        batch_size = int(args.batch_size)

    ingest_json = read_json(data_location)
    if "openapi_url" not in ingest_json:
        ingest_json["openapi_url"] = (
            "https://raw.githubusercontent.com/CanDIG/katsu/develop/chord_metadata_service/mohpackets/docs/schemas/schema.yml"
        )

    results = {}
    json_data, status_code = prep_check_clinical_data(ingest_json, token, batch_size)
    schemas_to_ingest = list(json_data.keys())
    for program_id in schemas_to_ingest:
        program = json_data[program_id]
        schemas = program.pop("schemas")
        ingest_results, status_code = ingest_schemas(schemas)
        results[program_id] = ingest_results

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    initialize()
    main()
