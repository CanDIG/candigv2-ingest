import unittest

from tests.test_auth import *

if __name__ == '__main__':
    if os.environ.get("CANDIG_URL") is None:
        print("ERROR: ENV is not set. Did you forget to run 'source env.sh'?")
        exit()
    print("Running unit tests...")
    unittest.main()