import json
import argparse
import threading
import requests
from concurrent.futures import ThreadPoolExecutor


def parse_args():
    parser = argparse.ArgumentParser(description="Extract all drs objects associated with the biosamples endpoint result.")
    parser.add_argument('--file', type=str, required=False, help="File with output of biosamples call")
    parser.add_argument('--url', type=str, required=True, help="URL of the candig deployment you are retrieving data from")
    parser.add_argument('--token', type=str, required=True, help="site admin token for the candig deployment you are retrieving data from.")
    parser.add_argument('--output', type=str, required=True, help="output file to write to")
    parser.add_argument('--workers', type=int, default=8, help="number of concurrent requests to make to DRS")

    args = parser.parse_args()
    return args


class Unauthorized(Exception):
    pass


class DrsClient:
    def __init__(self, url, headers, workers):
        self.url = f"{url}/drs/ga4gh/drs/v1"
        self.headers = headers
        self.local = threading.local()
        self.cache = {}  # drs object id -> object, or None if it couldn't be retrieved
        self.workers = workers

    def session(self):
        # one keep-alive session per thread, so we don't renegotiate TLS on every request
        if not hasattr(self.local, "session"):
            self.local.session = requests.Session()
            self.local.session.headers.update(self.headers)
            adapter = requests.adapters.HTTPAdapter(pool_maxsize=self.workers)
            self.local.session.mount("http://", adapter)
            self.local.session.mount("https://", adapter)
        return self.local.session

    def preload_program(self, program_id):
        # fetch every object in a program in one call, rather than one call per object
        response = self.session().get(f"{self.url}/objects", params={"program_id": program_id})
        if response.status_code == 401:
            raise Unauthorized(response.text)
        if response.status_code != 200:
            print(f"Couldn't preload program {program_id}: {response.status_code}; falling back to per-object requests")
            return
        for obj in response.json():
            self.cache[obj["id"]] = obj
        print(f"Preloaded {program_id}")

    def get_object(self, obj_id):
        if obj_id in self.cache:
            return self.cache[obj_id]
        response = self.session().get(f"{self.url}/objects/{obj_id}")
        if response.status_code == 401:
            # token is unauthorized/expired
            raise Unauthorized(response.text)
        obj = response.json() if response.status_code == 200 else None
        self.cache[obj_id] = obj
        return obj


def gather_related(client, drs_obj_ids, contents_types):
    sub_drs_objs = list(drs_obj_ids)
    related_objs = []
    seen = set()
    errors = []
    while len(sub_drs_objs) > 0:
        sub_drs_obj_id = sub_drs_objs.pop(0)
        if sub_drs_obj_id not in seen:
            seen.add(sub_drs_obj_id)
            related_objs.append(sub_drs_obj_id)
        obj = client.get_object(sub_drs_obj_id)
        if obj is None:
            errors.append(sub_drs_obj_id)
            continue
        for i in obj.get("contents", []):
            if i["id"] != i["name"] and i["id"] not in contents_types:
                # ExperimentContentsObjects are the only ones that fit this, and we've already accounted for these:
                # the name is the submitter_sample_id of the experiment in the MoH model
                # the id is the id of the ExperimentDrsObject
                continue
            elif i["name"] not in seen:
                seen.add(i["name"])
                sub_drs_objs.append(i["name"])
                related_objs.append(i["name"])
    return related_objs, errors


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

    experiment_drs_objects = {}
    sample_programs = {}
    for sample in biosamples:
        # collect all of the ExperimentDrsObjects
        experiments = sample["experiments"]["wgs"] + sample["experiments"]["wts"]
        if len(experiments) > 0:
            experiment_drs_objects[sample["biosample_id"]] = experiments
            sample_programs[sample["biosample_id"]] = sample["program"]
    programs = set(sample_programs.values())

    print(f"Gathered experiment drs objects for {len(experiment_drs_objects)} samples in {len(programs)} programs")
    contents_types = ["analysis", "variant", "read", "transcript", "index"]
    client = DrsClient(args.url, headers, args.workers)

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            list(executor.map(client.preload_program, sorted(programs)))

        result = {}
        errors = []
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                sample_id: executor.submit(gather_related, client, drs_obj_ids, contents_types)
                for sample_id, drs_obj_ids in experiment_drs_objects.items()
            }
            for n, (sample_id, future) in enumerate(futures.items(), start=1):
                related_objs, sample_errors = future.result()
                result[sample_id] = related_objs
                errors.extend(e for e in sample_errors if e not in errors)
                if n % 100 == 0 or n == len(futures):
                    print(f"Processed {n}/{len(futures)} samples")
    except Unauthorized as e:
        print(e)
        return

    with open(args.output, "w") as f:
        # programs records each sample's program at extraction time, so reset_programs.py knows which programs to list
        json.dump({"result": result, "programs": sample_programs, "errors": errors}, f, indent=2)


if __name__ == "__main__":
    main()
