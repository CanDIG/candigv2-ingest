import sys
import argparse
import json
import requests
import os
import auth


def update_user_dataset(user, dataset, opa_url, token):
	headers = {"Authorization": f"Bearer {token}"}
	# get current access:
	access = requests.get(opa_url + "/v1/data/access", headers=headers).json()
	if "result" not in access:
		raise Exception(f"OPA error: {access}")
	controlled_access_list = access["result"]["controlled_access_list"]
	if user in controlled_access_list:
		if dataset not in controlled_access_list[user]:
			controlled_access_list[user].append(dataset)
	else:
		controlled_access_list[user] = [dataset]
	
	# put back:
	response = requests.put(opa_url + "/v1/data/access", headers=headers, json=access["result"])
	if response.status_code == 204:
		access = requests.get(opa_url + "/v1/data/access", headers=headers).json()
		return {"access": access["result"]}
	raise Exception(f"OPA error: {access.status_code}")

def main():
	parser = argparse.ArgumentParser(description="Script to add authorization of a dataset to a user in Opa.")
	
	parser.add_argument("--user", help="user name", required=False)
	parser.add_argument("--userfile", help="user file", required=False)
	parser.add_argument("--dataset", help="dataset name")
	parser.add_argument("--opa_url", help="Opa URL")
	
	args = parser.parse_args()
	token = auth.get_site_admin_token()
	
	if args.userfile is not None:
		with open(args.userfile) as f:
			lines = f.readlines()
			for line in lines:
				last = update_user_dataset(line.strip(), args.dataset, args.opa_url, token)
			print(json.dumps(last, indent=4))
	elif args.user is not None:
		print(json.dumps(update_user_dataset(args.user, args.dataset, args.opa_url, token), indent=4))
	else:
		raise Exception("Either a user name or a file of users is required.")


if __name__ == "__main__":
	main()
