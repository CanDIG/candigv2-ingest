import authx.auth
import os
import re
import jwt
import requests


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
    return False


def get_refresh_token(token):
    client_secret = authx.auth.get_service_store_secret(service="keycloak", key="client-secret")
    return authx.auth.get_oauth_response(
        client_secret = client_secret,
        refresh_token=token
        )
