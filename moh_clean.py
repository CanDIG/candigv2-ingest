from http import HTTPStatus

import requests

url = "http://example.com/api/delete"

response = input("Are you sure you want to delete the database? (yes/no): ")

if response == "yes":
    katsu_server_url = "http://127.0.0.1:8000"
    delete_url = "/api/v1/delete/all"
    url = katsu_server_url + delete_url
    headers = {"Content-Type": "application/json"}
    res = requests.delete(url)
    if res.status_code == HTTPStatus.NO_CONTENT:
        print(f"Delete successful with status code {res.status_code}")
    else:
        print(
            f"Delete failed with status code {res.status_code} and message: {res.text}"
        )
else:
    print("Delete cancelled")
