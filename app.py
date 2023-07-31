from connexion import FlaskApp
from flask import url_for, redirect

import katsu_ingest
import htsget_ingest

def root():
    return redirect(url_for('ingest_operations_get_service_info'))

def create_app():
    connexionApp = FlaskApp(__name__, specification_dir='./')
    connexionApp.add_api('ingest_openapi.yaml', pythonic_params=True, strict_validation=True)
    app = connexionApp.app
    app.register_blueprint(katsu_ingest.ingest_blueprint)
    app.register_blueprint(htsget_ingest.ingest_blueprint)
    app.add_url_rule('/', 'root', root)
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(port=1236)