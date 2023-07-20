import connexion
from flask import request, Flask
import os
import os.path
import re
import authz
from markupsafe import escape
from urllib.parse import parse_qs, urlparse, urlencode


app = Flask(__name__)


# API endpoints
def get_service_info():
    return {
        "id": "org.candig.drs",
        "name": "CanDIG baby DRS service",
        "type": {
            "group": "org.ga4gh",
            "artifact": "drs",
            "version": "v1.2.0"
        },
        "description": "A DRS-compliant server for CanDIG genomic data",
        "organization": {
            "name": "CanDIG",
            "url": "https://www.distributedgenomics.ca"
        },
        "version": "1.0.0"
    }


@app.route('/ga4gh/drs/v1/objects/<path:object_id>')
def get_object(object_id, expand=False):
    app.logger.warning(f"looking for object {object_id}")
    access_url_parse = re.match(r"(.+?)/access_url/(.+)", escape(object_id))
    if access_url_parse is not None:
        return get_access_url(access_url_parse.group(1), access_url_parse.group(2))
    new_object = None
    if object_id is not None:
        new_object = database.get_drs_object(escape(object_id), expand)
        auth_code = authz.is_authed(escape(object_id), request)
        if auth_code != 200:
            return {"message": f"Not authorized to access object {object_id}"}, auth_code
    if new_object is None:
        return {"message": "No matching object found"}, 404
    return new_object, 200
