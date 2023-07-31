import connexion
from flask import request, Flask
import os

from ingest_result import *
from katsu_ingest import ingest_donor_with_clinical, setTrailingSlash
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
    return None, 501

def add_moh_variant(program_id):
    print(connexion.request.json)
    return None, 501

def add_clinical_donors():
    if os.environ.get("KATSU_TRAILING_SLASH") == "TRUE":
        setTrailingSlash(True)
    katsu_server_url = os.environ.get("CANDIG_URL")
    dataset = connexion.request.json
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
    elif type(response) == IngestUserException:
        return {"result": "Data error: %s" % response.value}, 400
    return "Unknown error", 500