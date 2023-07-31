import connexion
from flask import request, Flask

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
    print(connexion.request.json)
    return None, 501