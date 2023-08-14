from connexion import FlaskApp
from flask import url_for, redirect
import os

def root():
    return redirect(url_for('ingest_operations_get_service_info'))

def create_app():
    if not os.getenv("CANDIG_URL"):
        print("ERROR: CANDIG_URL not found. CanDIG stack environment variables likely not set. Please do so before "
              "running the service.")
        exit()
    connexionApp = FlaskApp(__name__, specification_dir='./')
    connexionApp.add_api('ingest_openapi.yaml', pythonic_params=True, strict_validation=True)
    app = connexionApp.app
    app.add_url_rule('/', 'root', root)
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(port=1236)