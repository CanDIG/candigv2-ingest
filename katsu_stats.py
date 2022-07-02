import sys
import argparse
import json
import requests
import auth
import os

"""
Gives some stats about what is in katsu

Lists projects, datasets, individuals
"""

TOKEN = auth.get_site_admin_token()

def list_data_type(katsu_server_url, data_type):
    """
    Lists the current datasets.
    Does not currently handle pagination for individuals, so you only get the first 25.
    """
    headers = {"Authorization": f"Bearer {TOKEN}"}

    results = requests.get(katsu_server_url + "/api/" + data_type, headers=headers)
    count = len(results.json()["results"])
    print(f"{data_type} (n={count}):")
    for r in results.json()["results"]:
        try:    
            # projects and datasets
            print(f"\t{r['title']}, uuid {r['identifier']}")
        except KeyError:
            # individuals
            print(f"\t{r['id']}")
            


def main():

    katsu_server_url = os.environ.get("CANDIG_URL")
    if katsu_server_url is None:
        raise Exception("CANDIG_URL environment variable is not set")
    else:
        katsu_server_url = katsu_server_url + "/katsu"

    data_type = "projects"
    list_data_type(katsu_server_url,data_type)
    data_type = "datasets"
    list_data_type(katsu_server_url,data_type)
    data_type = "individuals"
    list_data_type(katsu_server_url,data_type)

if __name__ == "__main__":
    main()
