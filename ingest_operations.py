import connexion
from flask import Flask
import os
import re
import traceback
import urllib.parse

import auth
import authx.auth
import katsu_ingest
import htsget_ingest
import config
import tempfile
import uuid
import json
from candigv2_logging.logging import CanDIGLogger


logger = CanDIGLogger(__file__)


app = Flask(__name__)

ERROR_CODES = {
    "SUCCESS": 0,
    "UNAUTHORIZED": 1,
    "VALIDATION": 2,
    "PROGRAMEXISTS": 3,
    "INTERNAL": 4,
    "AUTHORIZATIONERR": 5
}

def generateResponse(result, response_code):
    response_mapping = {
        0: ("Success", 200),
        1: ("Unauthorized", 403),
        2: ("Validation error", 422),
        3: ("Program exists", 422),
        4: ("Internal CanDIG error", 500),
        5: ("Authorization error", 401)
    }
    return {"result": result, "response_code": response_code,
            "response_message": response_mapping[response_code][0]}, response_mapping[response_code][1]

def get_headers():
    headers = {}
    if "Authorization" not in connexion.request.headers:
        return generateResponse("Bearer token required", ERROR_CODES["UNAUTHORIZED"])
    try:
        if not connexion.request.headers["Authorization"].startswith("Bearer "):
            return generateResponse("Invalid bearer token", ERROR_CODES["UNAUTHORIZED"])
        token = connexion.request.headers["Authorization"].split("Bearer ")[1]
        headers["Authorization"] = "Bearer %s" % token
    except Exception as e:
        if "Invalid bearer token" in str(e):
            return generateResponse("Bearer token invalid or unauthorized", ERROR_CODES["UNAUTHORIZED"])
        return generateResponse("Unknown error during authorization", ERROR_CODES["AUTHORIZATIONERR"])
    headers["Content-Type"] = "application/json"
    return headers


def check_default_site_admin(response):
    if auth.is_default_site_admin_set():
        if "warnings" not in response:
            response["warnings"] = []
        response["warnings"].append(f"Default site administrator {os.getenv('DEFAULT_SITE_ADMIN_USER')} is still configured. Use the /ingest/site-role/site_admin endpoint to set a different site admin.")


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

async def add_s3_credential():
    data = await connexion.request.json()
    token = connexion.request.headers['Authorization'].split("Bearer ")[1]
    if not authx.auth.is_action_allowed_for_program(token, method="POST", path="/ingest/s3-credential", program=None):
        return {"error": "Not authorized to store aws credentials"}, 403

    return authx.auth.store_aws_credential(endpoint=data["endpoint"], bucket=data["bucket"], access=data["access_key"], secret=data["secret_key"])


@app.route('/s3-credential/endpoint/<path:endpoint_id>/bucket/<path:bucket_id>')
def get_s3_credential(endpoint_id, bucket_id):
    token = connexion.request.headers['Authorization'].split("Bearer ")[1]
    if not authx.auth.is_action_allowed_for_program(token, method="GET", path="/ingest/s3-credential", program=None):
        return {"error": "Not authorized to view aws credentials"}, 403
    endpoint_cleaned = re.sub(r"\W", "_", endpoint_id)
    return authx.auth.get_aws_credential(endpoint=endpoint_cleaned, bucket=bucket_id)


@app.route('/s3-credential/endpoint/<path:endpoint_id>/bucket/<path:bucket_id>')
def delete_s3_credential(endpoint_id, bucket_id):
    token = connexion.request.headers['Authorization'].split("Bearer ")[1]
    if not authx.auth.is_action_allowed_for_program(token, method="DELETE", path="/ingest/s3-credential", program=None):
        return {"error": "Not authorized to remove aws credentials"}, 403
    endpoint_cleaned = re.sub(r"\W", "_", endpoint_id)
    return authx.auth.remove_aws_credential(endpoint=endpoint_cleaned, bucket=bucket_id)


####
# Site roles
####

@app.route('/site-role/<path:role_type>')
def list_role(role_type):
    try:
        token = connexion.request.headers['Authorization'].split("Bearer ")[1]
        if not authx.auth.is_action_allowed_for_program(token, method="GET", path="/ingest/site-role", program=None):
            return {"error": f"User not authorized to list site roles"}, 403

        result, status_code = authx.auth.get_role_type_in_opa(role_type)
        return result, status_code
    except Exception as e:
        return {"error": str(e)}, 500


@app.route('/site-role/<path:role_type>')
async def update_role(role_type):
    role_members = await connexion.request.json()
    try:
        token = connexion.request.headers['Authorization'].split("Bearer ")[1]
        if not authx.auth.is_action_allowed_for_program(token, method="POST", path="/ingest/site-role", program=None):
            return {"error": f"User not authorized to update site roles"}, 403

        result, status_code = authx.auth.set_role_type_in_opa(role_type, role_members)
        return result, status_code
    except Exception as e:
        return {"error": str(e)}, 500


@app.route('/site-role/<path:role_type>/email/<path:email>')
def is_user_in_role(role_type, email):
    try:
        token = connexion.request.headers['Authorization'].split("Bearer ")[1]

        if not authx.auth.is_action_allowed_for_program(token, method="GET", path="/ingest/site-role", program=None):
            return {"error": f"User not authorized to list site roles"}, 403

        result, status_code = authx.auth.get_role_type_in_opa(role_type)
        if status_code == 200:
            return (email in result[role_type]), 200
        return result, status_code
    except Exception as e:
        return {"error": str(e)}, 500


@app.route('/site-role/<path:role_type>/email/<path:email>')
def add_user_to_role(role_type, email):
    try:
        token = connexion.request.headers['Authorization'].split("Bearer ")[1]
        if not authx.auth.is_action_allowed_for_program(token, method="POST", path="/ingest/site-role", program=None):
            return {"error": f"User not authorized to add to site roles"}, 403

        result, status_code = authx.auth.get_role_type_in_opa(role_type)
        if status_code == 200:
            if email not in result[role_type]:
                result[role_type].append(email)
                result, status_code = authx.auth.set_role_type_in_opa(role_type, result[role_type])
        return result, status_code
    except Exception as e:
        return {"error": str(e)}, 500


@app.route('/site-role/<path:role_type>/email/<path:email>')
def remove_user_from_role(role_type, email):
    try:
        token = connexion.request.headers['Authorization'].split("Bearer ")[1]
        if not authx.auth.is_action_allowed_for_program(token, method="GET", path="/ingest/site-role", program=None):
            return {"error": f"User not authorized to remove users from site roles"}, 403

        result, status_code = authx.auth.get_role_type_in_opa(role_type)
        if status_code == 200:
            if email in result[role_type]:
                result[role_type].remove(email)
                result, status_code = authx.auth.set_role_type_in_opa(role_type, result[role_type])
            else:
                return {"error": f"User {email} not found in role {role_type}"}, 404
        return result, status_code
    except Exception as e:
        return {"error": str(e)}, 500

####
# Data ingest
####

async def add_genomic_linkages():
    dataset = await connexion.request.json()
    do_not_index = bool(connexion.request.query_params.get("do_not_index", False))
    headers = get_headers()
    token = connexion.request.headers['Authorization'].split("Bearer ")[1]
    response, status_code = htsget_ingest.check_genomic_data(dataset, token)
    if status_code == 200:
        ingest_uuid = add_to_queue({"htsget": response, "do_not_index": do_not_index})
        response = {"queue_id": ingest_uuid}
    check_default_site_admin(response)
    return response, status_code


async def add_clinical_donors():
    dataset = await connexion.request.json()
    batch_size = int(connexion.request.query_params.get("batch_size", 1000))
    headers = get_headers()
    token = connexion.request.headers['Authorization'].split("Bearer ")[1]
    response, status_code = katsu_ingest.prep_check_clinical_data(dataset, token, batch_size)
    if status_code == 200:
        ingest_uuid = add_to_queue({"katsu": response})
        response = {"queue_id": ingest_uuid}
    check_default_site_admin(response)
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

def list_programs():
    token = connexion.request.headers['Authorization'].split("Bearer ")[1]

    if not authx.auth.is_action_allowed_for_program(token, method="GET", path="/ingest/program", program=None):
        return {"error": f"User not authorized to list programs"}, 403

    response, status_code = authx.auth.list_programs_in_opa()
    return response, status_code


async def add_program():
    program = await connexion.request.json()
    token = connexion.request.headers['Authorization'].split("Bearer ")[1]

    if not authx.auth.is_action_allowed_for_program(token, method="POST", path="/ingest/program", program=program['program_id']):
        return {"error": f"User not authorized to add program {program['program_id']}"}, 403

    response, status_code = authx.auth.add_program_to_opa(program)
    check_default_site_admin(response)
    return response, status_code


@app.route('/program/<path:program_id>')
def get_program(program_id):
    token = connexion.request.headers['Authorization'].split("Bearer ")[1]

    if not authx.auth.is_action_allowed_for_program(token, method="GET", path="/ingest/program", program=program_id):
        return {"error": f"User not authorized to get program {program_id}"}, 403

    response, status_code = authx.auth.get_program_in_opa(program_id)
    return response, status_code


@app.route('/program/<path:program_id>')
def remove_program(program_id):
    token = connexion.request.headers['Authorization'].split("Bearer ")[1]

    if not authx.auth.is_action_allowed_for_program(token, method="DELETE", path="/ingest/program", program=program_id):
        return {"error": "User not authorized to remove programs"}, 403

    response = {"errors": {}}
    check_default_site_admin(response)

    opa_response, opa_status = authx.auth.remove_program_from_opa(program_id)
    katsu_response = katsu_ingest.delete_program(program_id, token)
    htsget_response = htsget_ingest.delete_program(program_id, token)

    if opa_status == 404:
        # htsget status is not included here because it doesn't have a 404 response
        return {"message": f"Program {program_id} not found"}, 404

    if opa_status != 200:
        response["errors"]["opa"] = {"message": opa_response, "status_code": opa_status}

    if katsu_response.status_code != 204 and katsu_response.status_code != 404:
        response["errors"]["katsu"] = {"message": katsu_response.text, "status_code": katsu_response.status_code}

    if htsget_response.status_code != 200:
        response["errors"]["htsget"] = {"message": htsget_response.text, "status_code": htsget_response.status_code}

    if len(response["errors"]) == 0:
        response.pop("errors")
        response["message"] = f"Program {program_id} successfully deleted"
        return response, 200

    return response, 500


####
# Pending users: approving a pending user creates a CanDIG-authorized user
####

def add_pending_user():
    token = connexion.request.headers['Authorization'].split("Bearer ")[1]

    response, status_code = authx.auth.add_pending_user_to_opa(token)
    return response, status_code


def list_pending_users():
    token = connexion.request.headers['Authorization'].split("Bearer ")[1]
    if not auth.is_site_admin(token):
        return {"error": f"User not authorized to list pending users"}, 403

    response, status_code = authx.auth.list_pending_users_in_opa()
    return {"results": response}, status_code


@app.route('/user/pending/<path:user_id>')
def approve_pending_user(user_id):
    token = connexion.request.headers['Authorization'].split("Bearer ")[1]
    if not auth.is_site_admin(token):
        return {"error": f"User not authorized to approve pending users"}, 403

    user_name = urllib.parse.unquote_plus(user_id)

    response, status_code = authx.auth.approve_pending_user_in_opa(user_name)
    return response, status_code


@app.route('/user/pending/<path:user_id>')
def reject_pending_user(user_id):
    token = connexion.request.headers['Authorization'].split("Bearer ")[1]
    if not auth.is_site_admin(token):
        return {"error": f"User not authorized to reject pending users"}, 403

    user_name = urllib.parse.unquote_plus(user_id)

    response, status_code = authx.auth.reject_pending_user_in_opa(user_name)
    return response, status_code


async def approve_pending_users():
    users = await connexion.request.json()
    token = connexion.request.headers['Authorization'].split("Bearer ")[1]
    if not auth.is_site_admin(token):
        return {"error": f"User not authorized to approve pending users"}, 403

    rejected = []
    for user_id in users:
        response, status_code = authx.auth.approve_pending_user_in_opa(user_id)
        if status_code != 200:
            rejected.append(user_id)
    if len(rejected) > 0:
        status_code = 401
        response = {"message": f"The following requested user IDs could not be approved: {rejected}"}

    return response, status_code


def clear_pending_users():
    token = connexion.request.headers['Authorization'].split("Bearer ")[1]

    if not auth.is_site_admin(token):
        return {"error": f"User not authorized to clear pending users"}, 403

    response, status_code = authx.auth.clear_pending_users_in_opa()
    return response, status_code


####
# DAC authorization for users
####

@app.route('/user/<path:user_id>')
def list_authz_for_user(user_id):
    token = connexion.request.headers['Authorization'].split("Bearer ")[1]

    response = ""
    status_code = 0
    if not authx.auth.is_action_allowed_for_program(token, method="GET", path=f"/ingest/user/{user_id}", program=None):
        return {"error": "User not authorized to list programs for user"}, 403

    if user_id == "me":
        user_id = authx.auth.get_user_id(request)

    user_result, status_code = authx.auth.get_user_in_opa(user_id)
    if status_code != 200:
        return user_result, status_code

    user_result["site_roles"] = []
    role_types, status_code = authx.auth.list_role_types_in_opa()
    if status_code == 200:
        for role_type in role_types:
            users, status_code = authx.auth.get_role_type_in_opa(role_type)
            if user_id in users[role_type]:
                user_result["site_roles"].append(role_type)

    user_result["program_authorizations"] = {}
    opa_permissions, status_code = authx.auth.get_opa_permissions(bearer_token=token, user_token=user_result["userinfo"]["sample_jwt"])
    if status_code == 200:
        user_result["program_authorizations"]["team_member"] = opa_permissions["team_member_programs"]
        user_result["program_authorizations"]["program_curator"] = opa_permissions["curator_programs"]

    user_result["program_authorizations"]["dac_authorizations"] = user_result.pop("dac_authorizations")

    return user_result, status_code


@app.route('/user/<path:user_id>')
def revoke_authz_for_user(user_id):
    token = connexion.request.headers['Authorization'].split("Bearer ")[1]

    if not authx.auth.is_action_allowed_for_program(token, method="DELETE", path=f"/ingest/user/{user_id}", program=None):
        return {"error": "User not authorized to revoke authorization for users"}, 403

    response, status_code = authx.auth.remove_user_from_opa(user_id)
    return response, status_code


@app.route('/user/<path:user_id>/dac_authorization')
async def add_dac_authz_for_user(user_id):
    program_dict = await connexion.request.json()
    token = connexion.request.headers['Authorization'].split("Bearer ")[1]

    if not authx.auth.is_action_allowed_for_program(token, method="POST", path="/ingest/user", program=program_dict["program_id"]):
        return {"error": "User not authorized to authorize programs for user"}, 403

    response, status_code = authx.auth.get_user_in_opa(user_id)
    if status_code != 200:
        # will return 404 if user is not authorized for CanDIG
        return response, status_code

    # we need to check to see if the program even exists in the system
    all_programs, status_code = authx.auth.list_programs_in_opa()
    if status_code != 200:
        return all_programs, status_code
    if program_dict["program_id"] not in all_programs:
        return {"error": f"Program {program_dict['program_id']} does not exist in {all_programs}"}
    response["dac_authorizations"][program_dict["program_id"]] = program_dict
    response, status_code = authx.auth.write_user_in_opa(response)
    return response, status_code


@app.route('/user/<path:user_id>/dac_authorization/<path:program_id>')
def get_dac_authz_for_user(user_id, program_id):
    token = connexion.request.headers['Authorization'].split("Bearer ")[1]

    if not authx.auth.is_action_allowed_for_program(token, method="GET", path="/ingest/user", program=None):
        return {"error": "User not authorized to get programs for user"}, 403

    response, status_code = authx.auth.get_user_in_opa(user_id)
    if status_code != 200:
        return response, status_code
    for p in response["dac_authorizations"]:
        if p == program_id:
            return p, 200
    return {"error": f"No program {program_id} found for user"}, status_code


@app.route('/user/<path:user_id>/authorize/<path:program_id>')
def remove_dac_authz_for_user(user_id, program_id):
    token = connexion.request.headers['Authorization'].split("Bearer ")[1]

    if not authx.auth.is_action_allowed_for_program(token, method="DELETE", path="/ingest/user", program=program_id):
        return {"error": "User not authorized to remove programs for user"}, 403

    response, status_code = authx.auth.get_user_in_opa(user_id)
    if status_code != 200:
        return response, status_code
    for p in response["dac_authorizations"]:
        if p == program_id:
            response["dac_authorizations"].pop(program_id)
            response, status_code = authx.auth.write_user_in_opa(response)
            return response, status_code
    return {"error": f"No program {program_id} found for user"}, status_code


@app.route('/get-token')
def get_token():
    # Attempt to grab the token via session_id
    if not hasattr(connexion.request, 'cookies'):
        return {'error': 'Unable to use the get-token endpoint without cookies'}, 200
    token = connexion.request.cookies['session_id']

    return {"token": token}, 200

    # Uncomment the below to exchange for a new token and return
    # that, instead
    # try:
    #    response = auth.get_refresh_token(token)
    #    if "error" in response:
    #        return {"error": response["error"]}, 500
    #    return {"token": response["refresh_token"]}, 200
    #except Exception as e:
    #    return {"error": str(e)}, 500
