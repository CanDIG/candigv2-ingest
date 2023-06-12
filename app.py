import connexion
from flask import Flask
import katsu_ingest

def create_app():
    app = Flask(__name__)
    app.register_blueprint(katsu_ingest.ingest_blueprint)
    return app
