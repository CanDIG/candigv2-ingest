import os
import requests
from unittest import TestCase

from auth import get_site_admin_token

KATSU_URL = os.environ.get("CANDIG_URL")

class TestAuth():
    def test_bearer_token(self):
        token = get_site_admin_token()
        version_request = requests.get(KATSU_URL + "/katsu/v2/version_check",
                                       headers={"Authorization": "Bearer %s" % token})
        assert version_request.status_code == 200



