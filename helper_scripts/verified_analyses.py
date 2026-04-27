import json
import argparse
import requests


def parse_args():
    parser = argparse.ArgumentParser(description="Get verified status of all analyses associated with the biosamples endpoint result.")
    parser.add_argument('--file', type=str, required=False, help="File with output of biosamples call")
    parser.add_argument('--url', type=str, required=True, help="URL of the candig deployment you are retrieving data from")
    parser.add_argument('--token', type=str, required=True, help="site admin token for the candig deployment you are retrieving data from.")
    parser.add_argument('--output', type=str, required=True, help="output file to write to")

    args = parser.parse_args()
    return args


def main():
    args = parse_args()

    headers = {"Authorization": f"Bearer {args.token}",
       "Content-Type": "application/json; charset=utf-8"}

    if args.file is not None:
        with open(args.file, "r") as f:
            biosamples = json.load(f)
    else:
        response = requests.post(f"{args.url}/drs/ga4gh/drs/v1/biosamples", headers=headers, json={})
        if response.status_code == 200:
            biosamples = response.json()
        else:
            print(f"Couldn't get a list of biosamples: {response.status_code} {response.text}")
            return

    result = []
    errors = []
    analyses = set()
    for sample in biosamples:
        if "analyses" in sample and len(sample["analyses"]) > 0:
            for type in sample["analyses"]:
                analyses.update(sample["analyses"][type])

    for analysis in analyses:
        response = requests.get(f"{args.url}/drs/ga4gh/drs/v1/objects/{analysis}", headers=headers)
        if response.status_code == 401:
            # token is unauthorized/expired
            print(response.text)
            return
        if response.status_code == 200:
            result.append(f"{analysis}, {response.json()["metadata"]["last_verified"]}")


    with open(args.output, "w") as f:
        for line in result:
            f.write(f"{line}\n")

if __name__ == "__main__":
    main()
