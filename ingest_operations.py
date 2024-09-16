import connexion
from flask import request, Flask
import os
import re
import traceback
import urllib.parse

import auth
from ingest_result import *
from katsu_ingest import prep_check_clinical_data
from htsget_ingest import check_genomic_data
from opa_ingest import remove_user_from_dataset, add_user_to_dataset
import config
import tempfile
import uuid
import json


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

def get_headers():
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
    return headers


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


####
# S3 credentials
####

def add_s3_credential():
    data = connexion.request.json
    token = request.headers['Authorization'].split("Bearer ")[1]
    return auth.store_s3_credential(data["endpoint"], data["bucket"], data["access_key"], data["secret_key"], token)


@app.route('/s3-credential/endpoint/<path:endpoint_id>/bucket/<path:bucket_id>')
def get_s3_credential(endpoint_id, bucket_id):
    token = request.headers['Authorization'].split("Bearer ")[1]
    endpoint_cleaned = re.sub(r"\W", "_", endpoint_id)
    return auth.get_s3_credential(endpoint_cleaned, bucket_id, token)


@app.route('/s3-credential/endpoint/<path:endpoint_id>/bucket/<path:bucket_id>')
def delete_s3_credential(endpoint_id, bucket_id):
    token = request.headers['Authorization'].split("Bearer ")[1]
    endpoint_cleaned = re.sub(r"\W", "_", endpoint_id)
    return auth.remove_s3_credential(endpoint_cleaned, bucket_id, token)


####
# Site roles
####

@app.route('/site-role/<path:role_type>')
def list_role(role_type):
    try:
        token = request.headers['Authorization'].split("Bearer ")[1]
        result, status_code = auth.get_role_type_in_opa(role_type, token)
        return result, status_code
    except Exception as e:
        return {"error": str(e)}, 500


@app.route('/site-role/<path:role_type>')
def update_role(role_type):
    role_members = connexion.request.json
    try:
        token = request.headers['Authorization'].split("Bearer ")[1]
        result, status_code = auth.set_role_type_in_opa(role_type, role_members, token)
        return result, status_code
    except Exception as e:
        return {"error": str(e)}, 500


@app.route('/site-role/<path:role_type>/email/<path:email>')
def is_user_in_role(role_type, email):
    try:
        token = request.headers['Authorization'].split("Bearer ")[1]
        result, status_code = auth.get_role_type_in_opa(role_type, token)
        if status_code == 200:
            return (email in result[role_type]), 200
        return result, status_code
    except Exception as e:
        return {"error": str(e)}, 500


@app.route('/site-role/<path:role_type>/email/<path:email>')
def add_user_to_role(role_type, email):
    try:
        token = request.headers['Authorization'].split("Bearer ")[1]
        result, status_code = auth.get_role_type_in_opa(role_type, token)
        if status_code == 200:
            result[role_type].append(email)
            result, status_code = auth.set_role_type_in_opa(role_type, result[role_type], token)
        return result, status_code
    except Exception as e:
        return {"error": str(e)}, 500


@app.route('/site-role/<path:role_type>/email/<path:email>')
def remove_user_from_role(role_type, email):
    try:
        token = request.headers['Authorization'].split("Bearer ")[1]
        result, status_code = auth.get_role_type_in_opa(role_type, token)
        if status_code == 200:
            if email in result[role_type]:
                result[role_type].remove(email)
                result, status_code = auth.set_role_type_in_opa(role_type, result[role_type], token)
            else:
                return {"error": f"User {email} not found in role {role_type}"}, 404
        return result, status_code
    except Exception as e:
        return {"error": str(e)}, 500

####
# Data ingest
####

def add_genomic_linkages():
    dataset = connexion.request.json
    do_not_index = bool(connexion.request.args.get("do_not_index", False))
    headers = get_headers()
    token = request.headers['Authorization'].split("Bearer ")[1]
    response, status_code = check_genomic_data(dataset, token)
    if status_code == 200:
        ingest_uuid = add_to_queue({"htsget": response, "do_not_index": do_not_index})
        response = {"queue_id": ingest_uuid}
    if auth.is_default_site_admin_set():
        response["warning"] = f"Default site administrator {os.getenv('DEFAULT_SITE_ADMIN_USER')} is still configured. Use the /ingest/site-role/site_admin endpoint to set a different site admin."
    return response, status_code


def add_clinical_donors():
    dataset = connexion.request.json
    batch_size = int(connexion.request.args.get("batch_size", 1000))
    headers = get_headers()
    token = request.headers['Authorization'].split("Bearer ")[1]
    response, status_code = prep_check_clinical_data(dataset, token, batch_size)
    if status_code == 200:
        ingest_uuid = add_to_queue({"katsu": response})
        response = {"queue_id": ingest_uuid}
    if auth.is_default_site_admin_set():
        response["warning"] = f"Default site administrator {os.getenv('DEFAULT_SITE_ADMIN_USER')} is still configured. Use the /ingest/site-role/site_admin endpoint to set a different site admin."
    return response, status_code


def add_to_queue(ingest_json):
    queue_id = str(uuid.uuid1())
    with tempfile.NamedTemporaryFile(delete_on_close=False, mode="w") as f:
        json.dump(ingest_json, f, indent=4)
        os.rename(f.name, os.path.join(config.DAEMON_PATH, "to_ingest", queue_id))
    results_path = os.path.join(config.DAEMON_PATH, "results", queue_id)
    with open(results_path, "w") as f:
        json.dump({"status": "still in queue"}, f)
    return queue_id


@app.route('/status/<path:queue_id>')
def get_ingest_status(queue_id):
    try:
        results_path = os.path.join(config.DAEMON_PATH, "results", queue_id)
        with open(results_path) as f:
            json_data = json.load(f)
            # os.remove(results_path)
            return json_data, 200
    except:
        return {"error": f"no such queue_id {queue_id}"}, 404


####
# Program authorizations
####

def list_program_authorizations():
    token = request.headers['Authorization'].split("Bearer ")[1]

    response, status_code = auth.list_programs_in_opa(token)
    return response, status_code


def add_program_authorization():
    program = connexion.request.json
    token = request.headers['Authorization'].split("Bearer ")[1]

    response, status_code = auth.add_program_to_opa(program, token)
    if auth.is_default_site_admin_set():
        response["warning"] = f"Default site administrator {os.getenv('DEFAULT_SITE_ADMIN_USER')} is still configured. Use the /ingest/site-role/site_admin endpoint to set a different site admin."
    return response, status_code


@app.route('/program/<path:program_id>')
def get_program_authorization(program_id):
    token = request.headers['Authorization'].split("Bearer ")[1]

    response, status_code = auth.get_program_in_opa(program_id, token)
    return response, status_code


@app.route('/program/<path:program_id>')
def remove_program_authorization(program_id):
    token = request.headers['Authorization'].split("Bearer ")[1]

    response, status_code = auth.remove_program_from_opa(program_id, token)
    return response, status_code


@app.route('/program/<path:program_id>/email/<path:email>')
def add_user_access(program_id, email):
    token = request.headers['Authorization'].split("Bearer ")[1]
    try:
        result, status_code = add_user_to_dataset(email, program_id, token)
        return result, status_code
    except Exception as e:
        return {"error": str(e)}, 500


@app.route('/program/<path:program_id>/email/<path:email>')
def remove_user_access(program_id, email):
    token = request.headers['Authorization'].split("Bearer ")[1]
    try:
        result, status_code = remove_user_from_dataset(email, program_id, token)
        return result, status_code
    except Exception as e:
        return {"error": str(e)}, 500

####
# Pending users
####

def add_pending_user():
    token = request.headers['Authorization'].split("Bearer ")[1]

    response, status_code = auth.add_pending_user_to_opa(token)
    return response, status_code


def list_pending_users():
    token = request.headers['Authorization'].split("Bearer ")[1]

    response, status_code = auth.list_pending_users_in_opa(token)
    return {"results": response}, status_code


@app.route('/user/pending/<path:user_id>')
def approve_pending_user(user_id):
    token = request.headers['Authorization'].split("Bearer ")[1]
    user_name = urllib.parse.unquote_plus(user_id)

    response, status_code = auth.approve_pending_user_in_opa(user_name, token)
    return response, status_code


@app.route('/user/pending/<path:user_id>')
def reject_pending_user(user_id):
    token = request.headers['Authorization'].split("Bearer ")[1]
    user_name = urllib.parse.unquote_plus(user_id)

    response, status_code = auth.reject_pending_user_in_opa(user_name, token)
    return response, status_code


def approve_pending_users():
    users = connexion.request.json
    token = request.headers['Authorization'].split("Bearer ")[1]

    rejected = []
    for user_id in users:
        response, status_code = auth.approve_pending_user_in_opa(user_id, token)
        if status_code != 200:
            rejected.append(user_id)
    if len(rejected) > 0:
        status_code = 401
        response = {"message": f"The following requested user IDs could not be approved: {rejected}"}

    return response, status_code


def clear_pending_users():
    token = request.headers['Authorization'].split("Bearer ")[1]

    response, status_code = auth.clear_pending_users_in_opa(token)
    return response, status_code

####
# DAC authorization for users
####

@app.route('/user/<path:user_id>/authorize')
def list_programs_for_user(user_id):
    token = request.headers['Authorization'].split("Bearer ")[1]
    user_name = urllib.parse.unquote_plus(user_id)
    response, status_code = auth.get_user_in_opa(user_name, token)
    if status_code != 200:
        return response, status_code
    print(response)
    return {"results": list(response["programs"].values())}, status_code


@app.route('/user/<path:user_id>/authorize')
def authorize_program_for_user(user_id):
    program_dict = connexion.request.json
    token = request.headers['Authorization'].split("Bearer ")[1]
    user_name = urllib.parse.unquote_plus(user_id)
    response, status_code = auth.get_user_in_opa(user_name, token)
    if status_code != 200:
        return response, status_code

    # we need to check to see if the program even exists in the system
    all_programs = auth.list_programs_in_opa(token)
    if program_dict["program_id"] not in all_programs:
        return {"error": f"Program {program_dict['program_id']} does not exist in {all_programs}"}
    response["programs"][program_dict["program_id"]] = program_dict
    response, status_code = auth.write_user_in_opa(response, token)
    return response, status_code


@app.route('/user/<path:user_id>/authorize/<path:program_id>')
def get_program_for_user(user_id, program_id):
    token = request.headers['Authorization'].split("Bearer ")[1]
    user_name = urllib.parse.unquote_plus(user_id)

    response, status_code = auth.get_user_in_opa(user_name, token)
    if status_code != 200:
        return response, status_code
    for p in response["programs"]:
        if p == program_id:
            return p, 200
    return {"error": f"No program {program_id} found for user"}, status_code


@app.route('/user/<path:user_id>/authorize/<path:program_id>')
def remove_program_for_user(user_id, program_id):
    token = request.headers['Authorization'].split("Bearer ")[1]
    user_name = urllib.parse.unquote_plus(user_id)

    response, status_code = auth.get_user_in_opa(user_name, token)
    if status_code != 200:
        return response, status_code
    for p in response["programs"]:
        if p == program_id:
            response["programs"].pop(program_id)
            response, status_code = auth.write_user_in_opa(response, token)
            return response, status_code
    return {"error": f"No program {program_id} found for user"}, status_code
