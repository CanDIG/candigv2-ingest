import os
import requests


def get_site_admin_token():
	payload = {
		"client_id": os.environ.get("CANDIG_CLIENT_ID"),
		"client_secret": os.environ.get("CANDIG_CLIENT_SECRET"),
		"grant_type": "password",
		"username": os.environ.get("CANDIG_SITE_ADMIN_USER"),
		"password": os.environ.get("CANDIG_SITE_ADMIN_PASSWORD"),
		"scope": "openid"
	}
	response = requests.post(f"{os.environ.get('KEYCLOAK_PUBLIC_URL')}/auth/realms/candig/protocol/openid-connect/token", data=payload)
	if response.status_code == 200:
		return response.json()["access_token"]
	else:
		raise Exception("Check for environment variables")
	

if __name__ == "__main__":
	print(get_site_admin_token())
