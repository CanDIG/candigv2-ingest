import os
import requests
from unittest import TestCase

from auth import get_site_admin_token

class TestAuth(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.katsu_url = os.environ.get("CANDIG_URL") + "/katsu"

    def test_bearer_token(self):
        token = get_site_admin_token()
        version_request = requests.get(self.katsu_url + "katsu/v2/version_check",
                                       headers={"Authorization": "Bearer %s" % token})
        self.assertEqual(version_request.status_code, 200)



