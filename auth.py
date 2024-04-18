import authx.auth
import os
import re
import json
import jwt
import requests
import urllib.parse


"""
For new auth model
def get_bearer_from_refresh(refresh_token):
    '''
    Transforms a refresh token into a usable bearer token through keycloak.
    Args:
        refresh_token: A Keycloak refresh token.
    Returns: A keycloak bearer token.
    '''
    return authx.auth.get_access_token(keycloak_url=os.getenv('KEYCLOAK_PUBLIC_URL'),
                                       client_id=os.getenv("CANDIG_CLIENT_ID"),
                                       client_secret=os.getenv('CANDIG_CLIENT_SECRET'),
                                       refresh_token=refresh_token)
"""

"""
For new auth model
def get_refresh_token(username=None, password=None, refresh_token=None):
    '''
    Returns a fresh Keycloak refresh token from either a username/password or existing refresh token.
    Args:
        username: If refresh token is not provided, a Keycloak username.
        password: If refresh token is not provided, a Keycloak password.
        refresh_token: If username/password are not provided, a Keycloak refresh token.

    Returns: A new Keycloak refresh token.

    '''
    if refresh_token:
        return authx.auth.get_refresh_token(
            keycloak_url=os.getenv('KEYCLOAK_PUBLIC_URL'),
            client_id=os.getenv('CANDIG_CLIENT_ID'),
            client_secret=os.getenv('CANDIG_CLIENT_SECRET'),
            refresh_token=refresh_token
        )
    if (username and password):
        return authx.auth.get_refresh_token(
            keycloak_url=os.getenv('KEYCLOAK_PUBLIC_URL'),
            client_id=os.getenv('CANDIG_CLIENT_ID'),
            client_secret=os.getenv('CANDIG_CLIENT_SECRET'),
            username=os.getenv(username),
            password=os.getenv(password)
        )
    else:
        raise ValueError("Username and password or refresh token required")
"""


def is_default_site_admin_set():
    if os.getenv("DEFAULT_SITE_ADMIN_USER") is not None:
        result, status_code = authx.auth.get_service_store_secret("opa", key=f"site_roles")
        if status_code == 200:
            if 'admin' in result['site_roles']:
                return os.getenv("DEFAULT_SITE_ADMIN_USER") in ",".join(result['site_roles']['admin'])
        raise Exception(f"ERROR: Unable to list site administrators {result} {status_code}")
    return False


def get_user_name(token):
    user_key = os.getenv("CANDIG_USER_KEY")
    decoded_jwt = jwt.decode(token, options={"verify_signature": False})
    if decoded_jwt is not None and user_key is not None and user_key in decoded_jwt:
        return decoded_jwt[user_key]
    return None


def is_site_admin(token):
    if (authx.auth.is_site_admin(None, token=token)):
        return True
    if os.getenv("OPA_SECRET") is None:
        print("OPA_SECRET is not set")
    return False


def is_authed(request: requests.Request):
    if 'Authorization' not in request.headers:
        return False

    """
    New auth model
    request_object = json.dumps({
        "url": request.url,
        "method": request.method,
        "headers": request.headers,
        "data": request.data
    })
    """
    request.path = request.url # Compatibility with old auth model

    # New auth model:
    # if (authx.auth.is_permissible(request_object)): return True
    if (authx.auth.is_site_admin(request)):
        return True
    return False

#####
# AWS stuff
#####

def get_minio_client(token, s3_endpoint, bucket, access_key=None, secret_key=None, region=None, secure=True):
    return authx.auth.get_minio_client(token=token, s3_endpoint=s3_endpoint, bucket=bucket, access_key=access_key, secret_key=secret_key, region=region, secure=secure)


def parse_aws_credential(awsfile):
    # parse the awsfile:
    access = None
    secret = None
    with open(awsfile) as f:
        lines = f.readlines()
        while len(lines) > 0 and (access is None or secret is None):
            line = lines.pop(0)
            parse_access = re.match(r"(aws_access_key_id|AWSAccessKeyId)\s*=\s*(.+)$", line)
            if parse_access is not None:
                access = parse_access.group(2)
            parse_secret = re.match(r"(aws_secret_access_key|AWSSecretKey)\s*=\s*(.+)$", line)
            if parse_secret is not None:
                secret = parse_secret.group(2)
    if access is None:
        return {"error": "awsfile did not contain access ID"}
    if secret is None:
        return {"error": "awsfile did not contain secret key"}
    return {"access": access, "secret": secret}


def store_aws_credential(endpoint, bucket, access, secret, token=None):
    return authx.auth.store_aws_credential(token=token, endpoint=endpoint, bucket=bucket,
                                           access=access, secret=secret)

#####
# Site roles
#####

def get_role_type_in_opa(role_type, token):
    if not is_site_admin(token):
        return {"error": "Only site admins can view site roles"}, 403
    result, status_code = authx.auth.get_service_store_secret("opa", key=f"site_roles")
    if status_code == 200:
        if role_type in result['site_roles']:
            return {role_type: result['site_roles'][role_type]}, 200
        return {"error": f"role type {role_type} does not exist"}, 404
    return result, status_code


def set_role_type_in_opa(role_type, members, token):
    if not is_site_admin(token):
        return {"error": "Only site admins can view site roles"}, 403
    result, status_code = authx.auth.get_service_store_secret("opa", key=f"site_roles")
    if status_code == 200:
        if role_type in result['site_roles']:
            result['site_roles'][role_type] = members
            result, status_code = authx.auth.set_service_store_secret("opa", key=f"site_roles", value=json.dumps(result))
            if status_code == 200:
                return result['site_roles'][role_type], status_code
        return {"error": f"role type {role_type} does not exist"}, 404
    return result, status_code


#####
# Program authorizations
#####

def add_program_to_opa(program_dict, token):
    # check to see if the user is allowed to add program authorizations:
    if not authx.auth.is_action_allowed_for_program(token, method="POST", path="ingest/program", program=program_dict['program_id']):
        return {"error": f"User not authorized to add program authorizations for program {program_dict['program_id']}"}, 403

    response, status_code = authx.auth.add_program_to_opa(program_dict)
    return response, status_code


def get_program_in_opa(program_id, token):
    # check to see if the user is allowed to add program authorizations:
    if not authx.auth.is_action_allowed_for_program(token, method="POST", path="ingest/program", program=program_id):
        return {"error": "User not authorized to add program authorizations"}, 403

    response, status_code = authx.auth.get_program_in_opa(program_id)
    return response, status_code


def remove_program_from_opa(program_id, token):
    # check to see if the user is allowed to add program authorizations:
    if not authx.auth.is_action_allowed_for_program(token, method="POST", path="ingest/program", program=program_id):
        return {"error": "User not authorized to add program authorizations"}, 403

    response, status_code = authx.auth.remove_program_from_opa(program_id)
    return response, status_code

#####
# Pending user authorizations
#####

def add_pending_user_to_opa(user_token):
    # NB: any user that has been authenticated by the IDP should be able to add themselves to the pending user list
    response, status_code = authx.auth.get_service_store_secret("opa", key=f"pending_users")
    if status_code != 200:
        return response, status_code

    user_name = get_user_name(user_token)
    if user_name is None:
        return {"error": "Could not verify jwt or obtain user ID"}, 403

    user_dict = {
        "user": {
            "user_name": user_name,
            "sample_jwt": user_token
        },
        "programs": {}
    }

    response["pending_users"][user_name] = user_dict

    response, status_code = authx.auth.set_service_store_secret("opa", key=f"pending_users", value=json.dumps(response))
    return response, status_code


def list_pending_users_in_opa(token):
    if not is_site_admin(token):
        return {"error": f"User not authorized to list pending users"}, 403

    response, status_code = authx.auth.get_service_store_secret("opa", key=f"pending_users")
    if status_code == 200:
        response = list(response["pending_users"].keys())
    return response, status_code


def approve_pending_user_in_opa(user_name, token):
    if not is_site_admin(token):
        return {"error": f"User not authorized to approve pending users"}, 403

    response, status_code = authx.auth.get_service_store_secret("opa", key=f"pending_users")
    if status_code != 200:
        return response, status_code
    pending_users = response["pending_users"]
    if user_name in pending_users:
        user_dict = pending_users[user_name]
        response2, status_code = write_user_in_opa(user_dict, token)
        if status_code == 200:
            pending_users.pop(user_name)
            response3, status_code = authx.auth.set_service_store_secret("opa", key=f"pending_users", value=json.dumps(response))
    else:
        return {"error": f"no pending user with ID {user_name}"}, 404
    return response, status_code


def reject_pending_user_in_opa(user_name, token):
    if not is_site_admin(token):
        return {"error": f"User not authorized to reject pending users"}, 403

    response, status_code = authx.auth.get_service_store_secret("opa", key=f"pending_users")
    if status_code != 200:
        return response, status_code
    pending_users = response["pending_users"]

    if user_name in pending_users:
        pending_users.pop(user_name)
        response, status_code = authx.auth.set_service_store_secret("opa", key=f"pending_users", value=json.dumps(response))
    else:
        return {"error": f"no pending user with ID {user_name}"}, 404
    return response, status_code


def clear_pending_users_in_opa(token):
    if not is_site_admin(token):
        return {"error": f"User not authorized to clear pending users"}, 403

    response, status_code = authx.auth.set_service_store_secret("opa", key="pending_users", value=json.dumps({"pending_users": {}}))
    return response, status_code

#####
# DAC authorization for users
#####

def write_user_in_opa(user_dict, token):
    if not is_site_admin(token):
        return {"error": f"User not authorized to add users"}, 403

    safe_name = urllib.parse.quote_plus(user_dict['user']['user_name'])
    response, status_code = authx.auth.set_service_store_secret("opa", key=f"users/{safe_name}", value=json.dumps(user_dict))
    return response, status_code


def get_user_in_opa(user_name, token):
    if not is_site_admin(token):
        return {"error": f"User not authorized to view users"}, 403

    safe_name = urllib.parse.quote_plus(user_name)
    response, status_code = authx.auth.get_service_store_secret("opa", key=f"users/{safe_name}")
    return response, status_code


def remove_user_from_opa(user_name, token):
    if not is_site_admin(token):
        return {"error": f"User not authorized to remove users"}, 403

    safe_name = urllib.parse.quote_plus(user_name)
    response, status_code = authx.auth.delete_service_store_secret("opa", key=f"users/{safe_name}")
    return response, status_code
