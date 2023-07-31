import connexion
from flask import request, Flask
import re
from markupsafe import escape

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
