import sys
import argparse
import json
import requests
import os
import auth
import re


CANDIG_URL = os.getenv("CANDIG_URL", "")
OPA_URL = CANDIG_URL + "/policy"


def add_user_to_dataset(user, dataset, token):
    headers = {"Authorization": f"Bearer {token}"}
    # get current access:
    access = requests.get(OPA_URL + "/v1/data/access", headers=headers).json()
    if "result" not in access:
        raise Exception(f"OPA error: {access}")
    controlled_access_list = access["result"]["controlled_access_list"]
    if user in controlled_access_list:
        if dataset not in controlled_access_list[user]:
            controlled_access_list[user].append(dataset)
    else:
        controlled_access_list[user] = [dataset]

    # put back:
    response = requests.put(OPA_URL + "/v1/data/access", headers=headers, json=access["result"])
    if response.status_code == 204:
        access = requests.get(OPA_URL + "/v1/data/access", headers=headers).json()
        return {"access": access["result"]}, 200
    return {"error": f"{response.status_code}: {response.text}"}, response.status_code


def remove_user_from_dataset(user, dataset, token):
    headers = {"Authorization": f"Bearer {token}"}
    # get current access:
    access = requests.get(OPA_URL + "/v1/data/access", headers=headers).json()
    if "result" not in access:
        raise Exception(f"OPA error: {access}")
    controlled_access_list = access["result"]["controlled_access_list"]
    if user in controlled_access_list:
        if dataset in controlled_access_list[user]:
            controlled_access_list[user].remove(dataset)
            # put back:
            response = requests.put(OPA_URL + "/v1/data/access", headers=headers, json=access["result"])
            if response.status_code == 204:
                access = requests.get(OPA_URL + "/v1/data/access", headers=headers).json()
                return {"access": access["result"]}
            return {"error": f"{response.status_code}: {response.text}"}, response.status_code
        return {"error": f"Program {dataset} not authorized for {user}"}, 404
    return {"error": f"User {user} not found"}, 404


def main():
    parser = argparse.ArgumentParser(description="Script to add authorization of a dataset to a user in Opa.")

    parser.add_argument("--user", help="user name", required=False)
    parser.add_argument("--userfile", help="user file", required=False)
    parser.add_argument("--dataset", help="dataset name", required=True)
    parser.add_argument("--remove", action='store_true', help="remove user access from dataset", required=False)

    args = parser.parse_args()
    token = auth.get_site_admin_token()
    if os.environ.get("CANDIG_URL") is None:
        raise Exception("CANDIG_URL environment variable is not set")
    if args.userfile is not None:
        with open(args.userfile) as f:
            lines = f.readlines()
            for line in lines:
                if re.match(r"^/s*$", line) is not None:
                    continue
                if args.remove:
                    last, status_code = remove_user_from_dataset(line.strip(), args.dataset, token)
                else:
                    last, status_code = add_user_to_dataset(line.strip(), args.dataset, token)
            print(json.dumps(last, indent=4))
    elif args.user is not None:
        if args.remove:
            print(json.dumps(remove_user_from_dataset(args.user, args.dataset, token), indent=4))
        else:
            print(json.dumps(add_user_to_dataset(args.user, args.dataset, token), indent=4))
    else:
        raise Exception("Either a user name or a file of users is required.")


if __name__ == "__main__":
    main()
