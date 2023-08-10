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
        return {"result": "Bearer token required"}, 401
    try:
        # New auth model
        # refresh_token = request.headers["Authorization"].split("Bearer ")[1]
        # token = auth.get_bearer_from_refresh(refresh_token)
        token = request.headers["Authorization"].split("Bearer ")[1]
        headers["Authorization"] = "Bearer %s" % token
    except Exception as e:
        if "Invalid bearer token" in str(e):
            return {"result": "Bearer token invalid or unauthorized"}, 401
        return {"result": "Unknown error during authorization"}, 401
    headers["Content-Type"] = "application/json"
    response = ingest_donor_with_clinical(katsu_server_url, dataset, headers)
    if type(response) == IngestResult:
        return {"result": "Ingested %d donors." % response.value}, 200
    elif type(response) == IngestPermissionsException:
        return {"result": "Permissions error: %s" % response.value, "note": "Data may be \
partially ingested. You may need to delete the relevant programs in Katsu."}, 403
    elif type(response) == IngestServerException:
        error_string = ','.join(response.value)
        return {"result": "Ingest encountered the following errors: %s" % error_string, "note": "Data may be partially \
ingested. You may need to delete the relevant programs in Katsu. This was an internal error, so you may want to report \
this issue to a CanDIG developer."}, 500
    elif isinstance(response, IngestUserException):
        result = {"result": "Data error: %s" % response.value}
        if type(response) == IngestValidationException:
            result["validation_errors"] = response.validation_errors
        return result, 400
    return "Unknown error", 500