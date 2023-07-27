from connexion import FlaskApp
import katsu_ingest
import htsget_ingest

VERSION = "2.0.0-alpha"

def get_service_info():
    return {
        "id": "org.candig.ingest",
        "name": "CanDIG Ingest Passthrough Service",
        "description": "A microservice used as a processing intermediary for ingesting data into Katsu and htsget",
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
