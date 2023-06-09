import connexion
from flask import Flask
import katsu_ingest

app = Flask(__name__)
app.register_blueprint(katsu_ingest.ingest_blueprint)
app.run(host='0.0.0.0', port=1235)
