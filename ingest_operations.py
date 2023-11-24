import connexion
from flask import request, Flask
import os
import traceback

import auth
from ingest_result import *
from katsu_ingest import ingest_clinical_data
from htsget_ingest import htsget_ingest
from opa_ingest import remove_user_from_dataset, add_user_to_dataset
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


@app.route('/program/<path:program_id>/email/<path:email>')
def add_user_access(program_id, email):
    token = request.headers['Authorization'].split("Bearer ")[1]
    try:
        result = add_user_to_dataset(email, program_id, token)
        return result, 200
    except Exception as e:
        return {"error": str(e)}, 500


@app.route('/program/<path:program_id>/email/<path:email>')
def remove_user_access(program_id, email):
    token = request.headers['Authorization'].split("Bearer ")[1]
    try:
        result = remove_user_from_dataset(email, program_id, token)
        return result, 200
    except Exception as e:
        return {"error": str(e)}, 500


def add_genomic_linkages():
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
    response, status_code = htsget_ingest(connexion.request.json, headers)
    return response, status_code

def add_clinical_donors():
    dataset = connexion.request.json
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
    response, status_code = ingest_clinical_data(dataset, headers)
    return response, status_code
