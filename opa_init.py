import sys
import argparse
import json
import requests


def update_user_dataset(user, dataset, opa_url, opa_secret):
	headers = {"Authorization": f"Bearer {opa_secret}"}
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
	
	parser.add_argument("user", help="user name")
	parser.add_argument("dataset", help="dataset name")
	parser.add_argument("opa_url", help="Opa URL")
	parser.add_argument("opa_secret", help="Opa admin secret")
	
	args = parser.parse_args()
	dataset = args.dataset
	user = args.user
	opa_url = args.opa_url
	opa_secret = args.opa_secret
	
	print(json.dumps(update_user_dataset(user, dataset, opa_url, opa_secret), indent=4))


if __name__ == "__main__":
	main()
