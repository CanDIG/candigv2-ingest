import os

from tests.unit.test_auth import *
from tests.integration.test_clinical_ingest import *

if __name__ == '__main__':
    if os.environ.get("CANDIG_URL") is None:
        print("ERROR: ENV is not set. Did you forget to run 'source env.sh'?")
        exit()
    print("Running tests...")
    pytest.main()