import os

from tests.unit.test_auth import *
from tests.integration.test_clinical_ingest import *

if os.getenv("PROD_ENVIRONMENT") == "TRUE":
    print("PRODUCTION ENVIRONMENT DETECTED - ABORTING TESTS\n"
          "Ingest tests require the deletion of some datasets which can be dangerous in a production environment. "
          "Please run them on a development environment instead.")
    exit()


if __name__ == '__main__':
    if os.environ.get("CANDIG_URL") is None:
        print("ERROR: ENV is not set. Did you forget to run 'source env.sh'?")
        exit()
    print("Running tests...")
    pytest.main()