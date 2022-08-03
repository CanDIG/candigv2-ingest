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


def list_data_type(katsu_server_url, data_type):
    """
    Lists the current datasets.
    Does not currently handle pagination for individuals, so you only get the first 25.
    """
    headers = auth.get_auth_header()

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
    parser.add_argument('--no_auth', action="store_true", help="Do not use authentication.")
    parser.add_argument('--katsu_url', help="Direct URL for katsu.", required=False)

    args = parser.parse_args()

    if args.no_auth:
        auth.AUTH = False
    else:
        auth.AUTH = True

    if args.katsu_url is None:
        if os.environ.get("CANDIG_URL") is None:
            raise Exception("Either CANDIG_URL must be set or a katsu_url argument must be provided")
        else:
            katsu_server_url = os.environ.get("CANDIG_URL") + "/katsu"
    else:
        katsu_server_url = args.katsu_url

    data_type = "projects"
    list_data_type(katsu_server_url,data_type)
    data_type = "datasets"
    list_data_type(katsu_server_url,data_type)
    data_type = "individuals"
    list_data_type(katsu_server_url,data_type)

if __name__ == "__main__":
    main()
