import sys
import argparse
import json
import requests
import auth

"""
An ingest script that automates the initial data ingest for katsu service.

You should run the script in an active virtualenv that has `requests` installed. You may also use Katsu's virtualenv for this purpose, if that's more convenient.

Please note that the data_file you supply must be available for Katsu to read. In other words, it should be located on the same server or within the same container as the Katsu instance.
"""

TOKEN = auth.get_site_admin_token()

def create_project(katsu_server_url, project_title):
    """
    Create a new Katsu project.

    Return the uuid of the newly-created project.
    """

    project_request = {
        "title": project_title,
        "description": "A new project."
    }
	headers = {"Authorization": f"Bearer {TOKEN}"}

    try:
        r = requests.post(katsu_server_url + "/api/projects", json=project_request, headers=headers)
    except requests.exceptions.ConnectionError:
        print(
            "Connection to the API server {} cannot be established.".format(
                katsu_server_url
            )
        )
        sys.exit()

    if r.status_code == 201:
        project_uuid = r.json()["identifier"]
        print(
            "Project {} with uuid {} has been created!".format(
                project_title, project_uuid
            )
        )
        return project_uuid
    elif r.status_code == 400:
        results = requests.get(katsu_server_url + "/api/projects")
        for r in results.json()["results"]:
            if r["title"] == project_title:
                return r["identifier"]
    else:
        print(r.json())
        sys.exit()


def create_dataset(katsu_server_url, project_uuid, dataset_title):
    """
    Create a new dataset.

    Return the uuid of newly-created dataset.
    """
    dataset_request = {
        "project": project_uuid,
        "title": dataset_title,
        "data_use": {
            "consent_code": {
                "primary_category": {"code": "GRU"},
                "secondary_categories": [{"code": "GSO"}],
            },
            "data_use_requirements": [{"code": "COL"}, {"code": "PUB"}],
        },
    }
    headers = {"Authorization": f"Bearer {TOKEN}"}

    r2 = requests.post(katsu_server_url + "/api/datasets", json=dataset_request, headers=headers)

    if r2.status_code == 201:
        dataset_uuid = r2.json()["identifier"]
        print(
            "Dataset {} with uuid {} has been created!".format(
                dataset_title, dataset_uuid
            )
        )
        return dataset_uuid
    elif r2.status_code == 400:
        results = requests.get(katsu_server_url + "/api/datasets")
        for r in results.json()["results"]:
            if r["title"] == dataset_title:
                return r["identifier"]
    else:
        print(r2.json())
        sys.exit()


def create_table(katsu_server_url, dataset_uuid, table_name, data_type):
    """
    Create a new katsu table.

    Return the uuid of the newly-created table.
    """

    table_request = {
        "name": table_name,
        "data_type": data_type,
        "dataset": dataset_uuid
    }
    headers = {"Authorization": f"Bearer {TOKEN}"}

    r3 = requests.post(katsu_server_url + "/tables", json=table_request, headers=headers)

    if r3.status_code == 200 or r3.status_code == 201:
        table_id = r3.json()["id"]
        print("Table {} with uuid {} has been created!".format(table_name, table_id))
        return table_id
    elif r3.status_code == 500:
        results = requests.get(katsu_server_url + "/api/tables")
        for r in results.json()["results"]:
            if r["name"] == table_name:
                return r["identifier"]
    else:
        print(r3.json())
        sys.exit()


def ingest_data(katsu_server_url, table_id, data_file, data_type):
    """
    Ingest the data file.
    """

    workflow_info = {
        "phenopacket": {
            "id": "phenopackets_json",
            "params": "phenopackets_json.json_document",
        },
        "mcodepacket": {
            "id": "mcode_json",
            "params": "mcode.json_document"
        }
    }
    
    workflow_params = {}
    workflow_params[workflow_info[data_type]["params"]] = data_file

    private_ingest_request = {
        "table_id": table_id,
        "workflow_id": workflow_info[data_type]['id'],
        "workflow_params": workflow_params,
        "workflow_outputs": {"json_document": data_file},
    }

    print("Ingesting {} data, this may take a while...".format(data_type))
    headers = {"Authorization": f"Bearer {TOKEN}"}

    r5 = requests.post(
        katsu_server_url + "/private/ingest", json=private_ingest_request, headers=headers
    )

    if r5.status_code == 200 or r5.status_code == 201 or r5.status_code == 204:
        print("{} Data have been ingested from source at {}".format(data_type, data_file))
    elif r5.status_code == 400:
        print(r5.text)
        sys.exit()
    else:
        print(
            "Something else went wrong when ingesting data, possibly due to duplications."
        )
        print(
            "Check you are using the absolute path of data_file, and make sure you aren't ingesting \
                duplicated data. Exception messages from Katsu printed below."
        )
        print(r5.text)
        sys.exit()


def main():
    parser = argparse.ArgumentParser(description="A script that facilitates initial data ingestion of Katsu service.")

    parser.add_argument("--dataset", help="Dataset name.")
    parser.add_argument("--input", help="The absolute path to the local data file, readable by Katsu.")

    args = parser.parse_args()
    dataset_title = args.dataset
    project_title = dataset_title
    table_name = dataset_title
    data_file = args.input
    data_type = "mcodepacket"

    katsu_server_url = os.environ.get("CANDIG_URL")
    if katsu_server_url is None:
        raise Exception("CANDIG_URL environment variable is not set")
    else:
        katsu_server_url = katsu_server_url + "/katsu"

    project_uuid = create_project(katsu_server_url, project_title)
    dataset_uuid = create_dataset(katsu_server_url, project_uuid, dataset_title)
    table_uuid = create_table(katsu_server_url, dataset_uuid, table_name, data_type)
    ingest_data(katsu_server_url, table_uuid, data_file, data_type)

if __name__ == "__main__":
    main()
