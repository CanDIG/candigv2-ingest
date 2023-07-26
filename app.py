from connexion import FlaskApp
import katsu_ingest
import htsget_ingest

VERSION = "2.0.0"

def info():
    info_string =  f"CanDIG ingest microservice {VERSION} "
    if __name__ == 'main':
        info_string += "running in development"
    else:
        info_string += "running on production"
    return info_string

def create_app():
    connexionApp = FlaskApp(__name__)
    app = connexionApp.app
    app.register_blueprint(katsu_ingest.ingest_blueprint)
    app.register_blueprint(htsget_ingest.ingest_blueprint)
    app.add_url_rule('/', 'info', info)
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(port=1236)