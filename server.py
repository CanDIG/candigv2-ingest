import connexion
from flask_cors import CORS
import candigv2_logging.logging

candigv2_logging.logging.initialize()

logger = candigv2_logging.logging.CanDIGLogger(__file__)


# Create the application instance
app = connexion.FlaskApp(__name__, specification_dir='./')
CORS(app.app)

app.add_api('ingest_openapi.yaml', pythonic_params=True, strict_validation=True)

if __name__ == '__main__':
    app.run(port=1236)
