import json
import argparse
import requests


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True, help="File with output of extract_drs.py")
    parser.add_argument('--corrected', type=str, required=True, help="File with correct mapping of samples to programs (csv, columns should be Submitter Sample ID, correct Program ID)")
    parser.add_argument('--url', type=str, required=True, help="URL of the candig deployment you are retrieving data from")
    parser.add_argument('--token', type=str, required=True, help="site admin token for the candig deployment you are retrieving data from.")

    args = parser.parse_args()
    return args


def main():
    args = parse_args()

    with open(args.input, "r") as f:
        experiments = json.load(f)
    with open(args.corrected, "r") as f:
        sample_lines = f.readlines()
        sample_lines.pop(0)
        sample_map = {}
        for line in sample_lines:
            #Submitter Sample ID,Program ID
            parts = line.split(",")
            sample_map[parts[0]] = parts[1]

    headers = {"Authorization": f"Bearer {args.token}",
           "Content-Type": "application/json; charset=utf-8"}

    experiment_drs_objects = []
    for sample_id in experiments["result"]:
        # find the matching program
        if sample_id in sample_map:
            program_id = sample_map[sample_id]
            # fix the related objects
            for drs_obj_id in experiments["result"][sample_id]:
                response = requests.get(f"{args.url}/drs/ga4gh/drs/v1/objects/{drs_obj_id}", headers=headers)
                if response.status_code == 200:
                    new_object = response.json()
                    print(f"in {drs_obj_id}: changing {new_object["program"]} to {program_id}")
                    new_object["program"] = program_id
                    response = requests.post(f"{args.url}/drs/ga4gh/drs/v1/objects", headers=headers, json=new_object)
                    print(response.status_code, response.text)

if __name__ == "__main__":
    main()
