import sys
import argparse
import json
import requests
import os
import auth
import re




def add_user_to_dataset(user, dataset, token):
    response, status_code = auth.get_program_in_opa(dataset, token)
    if status_code == 404:
        raise Exception(f"No program {dataset} exists")
    elif status_code >= 300:
        raise Exception(f"Error adding user authorization: {response}")
    if user not in response[dataset]["team_members"]:
        response[dataset]["team_members"].append(user)
    # put back:
    response, status_code = auth.add_program_to_opa(response[dataset], token)

    if status_code != 200:
        return {"error": f"{status_code}: {response}"}, status_code
    return auth.get_program_in_opa(dataset, token)


def remove_user_from_dataset(user, dataset, token):
    response, status_code = auth.get_program_in_opa(dataset, token)
    if status_code == 404:
        raise Exception(f"No program {dataset} exists")
    elif status_code >= 300:
        raise Exception(f"Error adding user authorization: {response}")
    if user in response[dataset]["team_members"]:
        response[dataset]["team_members"].remove(user)
        # put back:
        response, status_code = auth.add_program_to_opa(response[dataset], token)
        if status_code != 200:
            return {"error": f"{status_code}: {response}"}, status_code
        return auth.get_program_in_opa(dataset, token)
    else:
        return {"error": f"User {user} not found in program {dataset} team_members"}


def main():
    parser = argparse.ArgumentParser(description="Script to add authorization of a dataset to a user in Opa.")

    parser.add_argument("--user", help="user name", required=False)
    parser.add_argument("--userfile", help="user file", required=False)
    parser.add_argument("--dataset", help="dataset name", required=True)
    parser.add_argument("--remove", action='store_true', help="remove user access from dataset", required=False)

    args = parser.parse_args()
    token = auth.get_site_admin_token()
    if os.environ.get("OPA_URL") is None:
        raise Exception("OPA_URL environment variable is not set")
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
