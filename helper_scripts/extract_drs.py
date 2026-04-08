import json
import argparse
import requests


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, required=True, help="File with output of experiments call")
    parser.add_argument('--url', type=str, required=True, help="URL of the candig deployment you are retrieving data from")
    parser.add_argument('--token', type=str, required=True, help="site admin token for the candig deployment you are retrieving data from.")
    parser.add_argument('--output', type=str, required=True, help="output file to write to")

    args = parser.parse_args()
    return args


def main():
    args = parse_args()

    with open(args.file, "r") as f:
        experiments = json.load(f)

    experiment_drs_objects = {}
    for exp in experiments:
        # collect all of the ExperimentDrsObjects
        if len(exp["genomes"]) > 0:
            experiment_drs_objects[exp["experiment_id"]] = exp["genomes"]
        if len(exp["transcriptomes"]) > 0:
            experiment_drs_objects[exp["experiment_id"]] = exp["transcriptomes"]

    print("Gathered all experiment drs objects")
    result = {}
    errors = []
    headers = {"Authorization": f"Bearer {args.token}",
       "Content-Type": "application/json; charset=utf-8"}
    contents_types = ["analysis", "variant", "read", "transcript", "index"]

    while len(experiment_drs_objects) > 0:
        # gather all related drs objects
        sample_id = list(experiment_drs_objects.keys())[0]
        drs_obj_ids = experiment_drs_objects.pop(sample_id)
        sub_drs_objs = []
        sub_drs_objs.extend(drs_obj_ids)
        related_objs = []
        while len(sub_drs_objs) > 0:
            sub_drs_obj_id = sub_drs_objs.pop(0)
            if sub_drs_obj_id not in related_objs:
                related_objs.append(sub_drs_obj_id)
            response = requests.get(f"{args.url}/drs/ga4gh/drs/v1/objects/{sub_drs_obj_id}", headers=headers)
            if response.status_code == 401:
                # token is unauthorized/expired
                print(response.text)
                return
            if response.status_code == 200:
                contents = response.json()["contents"]
                for i in contents:
                    if i["id"] != i["name"] and i["id"] not in contents_types:
                        # ExperimentContentsObjects are the only ones that fit this, and we've already accounted for these:
                        # the name is the submitter_sample_id of the experiment in the MoH model
                        # the id is the id of the ExperimentDrsObject
                        continue
                    elif i["name"] not in related_objs:
                        sub_drs_objs.append(i["name"])
                        related_objs.append(i["name"])
            else:
                errors.append(sub_drs_obj_id)
        result[sample_id] = related_objs
        print(json.dumps({sample_id: related_objs}, indent=2))
        with open(args.output, "w") as f:
            json.dump({"result": result, "errors": errors}, f, indent=2)


if __name__ == "__main__":
    main()
