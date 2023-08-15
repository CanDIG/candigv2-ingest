import connexion
from flask import request, Flask
import os
import traceback

import auth
from ingest_result import *
from katsu_ingest import ingest_donor_with_clinical, setTrailingSlash
from htsget_ingest import htsget_ingest
import config

app = Flask(__name__)

ERROR_CODES = {
    "SUCCESS": 0,
    "UNAUTHORIZED": 1,
    "VALIDATION": 2,
    "COHORTEXISTS": 3,
    "INTERNAL": 4,
    "AUTHORIZATIONERR": 5
}

def generateResponse(result, response_code):
    response_mapping = {
        0: ("Success", 200),
        1: ("Unauthorized", 403),
        2: ("Validation error", 422),
        3: ("Cohort exists", 422),
        4: ("Internal CanDIG error", 500),
        5: ("Authorization error", 401)
    }
    return {"result": result, "response_code": response_code,
            "response_message": response_mapping[response_code][0]}, response_mapping[response_code][1]

# API endpoints
def get_service_info():
    return {
        "id": "org.candig.ingest",
        "name": "CanDIG Ingest Passthrough Service",
        "description": "A microservice used as a processing intermediary for ingesting data into Katsu and htsget",
        "organization": {
            "name": "CanDIG",
            "url": "https://www.distributedgenomics.ca"
        },
        "version": config.VERSION
    }

def add_s3_credential():
    data = connexion.request.json
    token = request.headers['Authorization'].split("Bearer ")[1]
    return auth.store_aws_credential(data["endpoint"], data["bucket"], data["access_key"], data["secret_key"], token)

def add_moh_variant(program_id):
    token = request.headers["Authorization"].split("Bearer ")[1]
    data = connexion.request.json
    """
    (For new auth model)
    try:
        token = auth.get_bearer_from_refresh(token)
    except Exception as e:
        return {"result": "Error validating token: %s" % str(e)}, 401
    """

    try:
        response = htsget_ingest(token, program_id, data)
    except Exception as e:
        traceback.print_exc()
        return {"result": "Unknown error (You may want to report this to a CanDIG developer): %s" % str(e)}, 500

    if type(response) == IngestResult:
        return {"result": "Ingested genomic sample: %s" % response.value}, 200
    elif type(response) == IngestUserException:
        return {"result": "Data error: %s" % response.value}, 400
    elif type(response) == IngestPermissionsException:
        return {"result": "Error: You are not authorized to write to program %s." % response.value}, 403
    elif type(response) == IngestServerException:
        return {"result": "Ingest encountered the following errors: %s" % response.value}, 500
    return 500

def add_clinical_donors():
    if os.environ.get("KATSU_TRAILING_SLASH") == "TRUE":
        setTrailingSlash(True)
    katsu_server_url = os.environ.get("CANDIG_URL")
    dataset = connexion.request.json["donors"]
    headers = {}
    if "Authorization" not in request.headers:
        return generateResponse("Bearer token required", ERROR_CODES["UNAUTHORIZED"])
    try:
        # New auth model
        # refresh_token = request.headers["Authorization"].split("Bearer ")[1]
        # token = auth.get_bearer_from_refresh(refresh_token)
        if not request.headers["Authorization"].startswith("Bearer "):
            return generateResponse("Invalid bearer token", ERROR_CODES["UNAUTHORIZED"])
        token = request.headers["Authorization"].split("Bearer ")[1]
        headers["Authorization"] = "Bearer %s" % token
    except Exception as e:
        if "Invalid bearer token" in str(e):
            return generateResponse("Bearer token invalid or unauthorized", ERROR_CODES["UNAUTHORIZED"])
        return generateResponse("Unknown error during authorization", ERROR_CODES["AUTHORIZATIONERR"])
    headers["Content-Type"] = "application/json"
    response = ingest_donor_with_clinical(katsu_server_url, dataset, headers)
    if type(response) == IngestResult:
        return generateResponse("Ingested %d donors." % response.value, ERROR_CODES["SUCCESS"])
    elif type(response) == IngestPermissionsException:
        return generateResponse(f"Permission error: {response.value} Data may be "
                                "partially ingested. You may need to delete the relevant programs in Katsu.",
                                ERROR_CODES["UNAUTHORIZED"])
    elif type(response) == IngestServerException:
        error_string = ','.join(response.value)
        return generateResponse(f"Ingest encountered the following errors: {error_string} "
                "Data may be partially ingested. You may need to delete the relevant programs in Katsu. "
                "This was an internal error, so you may want to report this issue to a CanDIG developer.",
                                ERROR_CODES["INTERNAL"])
    elif type(response) == IngestValidationException:
        return {"result": response.value, "validation_errors": response.validation_errors,
                "response_code": 2, "response_message": "Validation error"}
    elif type(response) == IngestCohortException:
        return generateResponse(response.value, 3)
