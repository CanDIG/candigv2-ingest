from connexion import FlaskApp

import katsu_ingest
import htsget_ingest


def create_app():
    connexionApp = FlaskApp(__name__, specification_dir='./')
    connexionApp.add_api('ingest_openapi.yaml', pythonic_params=True, strict_validation=True)
    app = connexionApp.app
    app.register_blueprint(katsu_ingest.ingest_blueprint)
    app.register_blueprint(htsget_ingest.ingest_blueprint)
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(port=1236)