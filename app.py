from connexion import FlaskApp
import katsu_ingest
import htsget_ingest

VERSION = "2.0.0"

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
        "version": VERSION
    }

def create_app():
    connexionApp = FlaskApp(__name__)
    app = connexionApp.app
    app.register_blueprint(katsu_ingest.ingest_blueprint)
    app.register_blueprint(htsget_ingest.ingest_blueprint)
    app.add_url_rule('/', 'info', get_service_info)
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(port=1236)