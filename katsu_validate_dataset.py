import sys
import argparse
import json
import requests
import auth
import os
from jsoncomparison import Compare

"""
An ingest script that automates the initial data ingest for katsu service.

You should run the script in an active virtualenv that has `requests` installed. You may also use Katsu's virtualenv for this purpose, if that's more convenient.

Please note that the data_file you supply must be available for Katsu to read. In other words, it should be located on the same server or within the same container as the Katsu instance.
"""


def get_dataset(katsu_server_url, dataset):
    """
    Get a dataset from katsu
    """

    headers = auth.get_auth_header()

    r = requests.get(katsu_server_url + "/api/mcodepackets", params={"datasets": dataset}, headers=headers)
    if r.status_code == 200:
        return r.json()["results"]
    else:
        print(f"{r.status_code} Problem getting dataset {dataset}")
        print(r.text)
        return []


def main():
    parser = argparse.ArgumentParser(description="A script that facilitates initial data ingestion of Katsu service.")

    parser.add_argument("--dataset", help="Dataset name.")
    parser.add_argument("--input", help="Local copy of mcodepacket file uploaded to Katsu.")

    args = parser.parse_args()
    dataset_title = args.dataset
    data_file = args.input
    data_type = "mcodepacket"

    katsu_server_url = os.environ.get("CANDIG_URL")
    if katsu_server_url is None:
        raise Exception("CANDIG_URL environment variable is not set")
    else:
        katsu_server_url = katsu_server_url + "/katsu"

    actual = get_dataset(katsu_server_url, dataset_title)
    expected = {}
    with open(args.input) as f:
        expected = json.load(f)

    compare = Compare().check(expected, actual)
    print("Katsu returned the following:")
    print(json.dumps(actual, indent=4))
    print("\n\nDifferences between expected and actual:")
    print(json.dumps(compare, indent=4))

if __name__ == "__main__":
    main()
