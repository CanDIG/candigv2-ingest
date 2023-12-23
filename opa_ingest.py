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
    # get current access:
    access, status_code = auth.get_opa_access()
    if status_code != 200:
        raise Exception(f"OPA error: {access}")
    controlled_access_list = access["access"]["controlled_access_list"]
    if user in controlled_access_list:
        if dataset not in controlled_access_list[user]:
            controlled_access_list[user].append(dataset)
    else:
        controlled_access_list[user] = [dataset]

    # put back:
    response, status_code = auth.set_opa_access(access)
    if status_code != 200:
        return {"error": f"{status_code}: {response}"}, status_code
    return response, 200


def remove_user_from_dataset(user, dataset, token):
    # get current access:
    access, status_code = auth.get_opa_access()
    if status_code != 200:
        raise Exception(f"OPA error: {access}")
    controlled_access_list = access["access"]["controlled_access_list"]
    if user in controlled_access_list:
        if dataset in controlled_access_list[user]:
            controlled_access_list[user].remove(dataset)
            # put back:
            response, status_code = auth.set_opa_access(access)
            if status_code != 200:
                return {"error": f"{status_code}: {response}"}, status_code
            return access, 200
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
