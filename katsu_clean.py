import sys
import argparse
import json
import requests


def get_uuids(katsu_server_url, dataset_title):
    results = requests.get(katsu_server_url + "/api/datasets")
    for r in results.json()["results"]:
        if r["title"] == dataset_title:
            return r["identifier"], r["project"]
    return None


def delete_dataset(katsu_server_url, dataset_uuid):
    return requests.delete(katsu_server_url + f"/api/datasets/{dataset_uuid}")


def delete_project(katsu_server_url, project_uuid):
    return requests.delete(katsu_server_url + f"/api/projects/{project_uuid}")


def delete_data(katsu_server_url, data_file, data_type):
    with open(data_file) as f:
        packets = json.load(f)
        for p in packets:
            r = requests.delete(katsu_server_url + f"/api/{data_type}s/{p['id']}")


def main():
    parser = argparse.ArgumentParser(description="A script that facilitates initial data ingestion of Katsu service.")

    parser.add_argument("project", help="Project name.")
    parser.add_argument("dataset", help="Dataset name.")
    parser.add_argument("table", help="Table name.")
    parser.add_argument("server_url", help="The URL of Katsu instance.")
    parser.add_argument("data_file", help="The absolute path to the local data file, readable by Katsu.")
    parser.add_argument("data_type", help="The type of data. Only phenopacket and mcodepacket are supported.")

    args = parser.parse_args()
    project_title = args.project
    dataset_title = args.dataset
    table_name = args.table
    katsu_server_url = args.server_url
    data_file = args.data_file
    data_type = args.data_type

    if data_type not in ['phenopacket', 'mcodepacket']:
        print("Data type must be either phenopacket or mcodepacket.")
        sys.exit()
    
    dataset_uuid, project_uuid = get_uuids(katsu_server_url, dataset_title)
    delete_data(katsu_server_url, data_file, data_type)
    delete_dataset(katsu_server_url, dataset_uuid)
    delete_project(katsu_server_url, project_uuid)
    
if __name__ == "__main__":
    main()
