import sys
import argparse
import json
import requests
import auth

TOKEN = auth.get_site_admin_token()


def get_uuids(katsu_server_url, dataset_title):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    results = requests.get(katsu_server_url + "/api/datasets", headers=headers)
    for r in results.json()["results"]:
        if r["title"] == dataset_title:
            return r["identifier"], r["project"]
    return None


def delete_dataset(katsu_server_url, dataset_uuid):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    return requests.delete(katsu_server_url + f"/api/datasets/{dataset_uuid}", headers=headers)


def delete_project(katsu_server_url, project_uuid):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    return requests.delete(katsu_server_url + f"/api/projects/{project_uuid}", headers=headers)


def delete_data(katsu_server_url, data_file, data_type):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    with open(data_file) as f:
        packets = json.load(f)
        for p in packets:
            r = requests.delete(katsu_server_url + f"/api/{data_type}s/{p['id']}", headers=headers)


def main():
    parser = argparse.ArgumentParser(description="A script that facilitates initial data ingestion of Katsu service.")

    parser.add_argument("dataset", help="Dataset name.")
    parser.add_argument("server_url", help="The URL of Katsu instance.")
    parser.add_argument("data_file", help="The absolute path to the local data file, readable by Katsu.")

    args = parser.parse_args()
    project_title = args.project
    dataset_title = args.dataset
    katsu_server_url = args.server_url

    katsu_server_url = os.environ.get("CANDIG_URL")
    if katsu_server_url is None:
        raise Exception("CANDIG_URL environment variable is not set")
    else:
        katsu_server_url = katsu_server_url + "/katsu"

    dataset_uuid, project_uuid = get_uuids(katsu_server_url, dataset_title)
    delete_data(katsu_server_url, data_file, data_type)
    delete_dataset(katsu_server_url, dataset_uuid)
    delete_project(katsu_server_url, project_uuid)
    
if __name__ == "__main__":
    main()
