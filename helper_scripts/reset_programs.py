import json
import argparse
import base64
import getpass
import time
import requests


def parse_args():
    parser = argparse.ArgumentParser(description="Given a list of drs objects returned from extract_drs.py and a list of updated mappings of samples to programs, update the drs objects to the correct programs.")
    parser.add_argument('--input', type=str, required=True, help="File with output of extract_drs.py")
    parser.add_argument('--corrected', type=str, required=True,
                        help="CSV File with correct mapping of samples to programs. Columns should be: "
                             "'Submitter Sample ID': the submitter sample id that links to all the objects that need to"
                             "be moved, "
                             "'Program ID': The program_id of the program that the objects should be moved to")
    parser.add_argument('--url', type=str, required=True, help="URL of the candig deployment for which you want to update data")
    parser.add_argument('--token', type=str, required=False, help="site admin token for the candig deployment for which you want to update data; "
                                                                   "if omitted, or when it expires, you'll be prompted for one")

    args = parser.parse_args()
    return args


def token_expiry(token):
    # read the exp claim without verifying; returns None if the token isn't a readable JWT
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))["exp"]
    except Exception:
        return None


class TokenSession:
    """Makes requests with a bearer token, asking for a new token when the current one expires."""

    def __init__(self, token):
        self.session = requests.Session()
        self.token = token or self.ask_for_token("No token given.")

    def ask_for_token(self, reason):
        print(reason)
        token = getpass.getpass("Paste a new site admin token (input hidden): ").strip()
        if not token:
            raise SystemExit("No token entered; stopping. Re-run to continue where this left off.")
        return token

    def request(self, method, url, **kwargs):
        while True:
            exp = token_expiry(self.token)
            # refresh a little early so the token doesn't expire mid-request
            if exp is not None and exp - time.time() < 30:
                self.token = self.ask_for_token("Token has expired or is about to expire.")
                continue
            headers = {"Authorization": f"Bearer {self.token}",
                       "Content-Type": "application/json; charset=utf-8"}
            response = self.session.request(method, url, headers=headers, **kwargs)
            if response.status_code in (401, 403):
                self.token = self.ask_for_token(f"Request was rejected ({response.status_code}): {response.text.strip()[:200]}")
                continue
            return response


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
            sample_map[parts[0].strip()] = parts[1].strip()

    client = TokenSession(args.token)

    drs_url = f"{args.url}/drs/ga4gh/drs/v1"

    # each object can be listed under more than one sample (e.g. tumour/normal pairs share a VCF),
    # so work out each object's target program once
    targets = {}
    conflicts = set()
    relevant_samples = [sample_id for sample_id in experiments["result"] if sample_id in sample_map]
    for sample_id in relevant_samples:
        for drs_obj_id in experiments["result"][sample_id]:
            if targets.setdefault(drs_obj_id, sample_map[sample_id]) != sample_map[sample_id]:
                conflicts.add(drs_obj_id)
    for drs_obj_id in conflicts:
        print(f"skipping {drs_obj_id}: its samples map to different programs")
        del targets[drs_obj_id]

    # only list the programs these objects can be in: the ones they're moving to (already moved by an earlier run)
    # and the ones they were in when extract_drs.py ran (missing from older extract_drs.py output)
    source_programs = experiments.get("programs", {})
    programs = set(targets.values()) | {source_programs[s] for s in relevant_samples if s in source_programs}

    # list objects one program at a time, rather than one GET per object
    current_objects = {}
    for program in sorted(programs):
        response = client.request("GET", f"{drs_url}/objects", params={"program_id": program})
        if response.status_code != 200:
            # large programs can time out at the gateway; their objects are fetched one at a time below
            print(f"Couldn't list objects for {program}: {response.status_code}; will fetch its objects individually")
            continue
        for obj in response.json():
            current_objects[obj["id"]] = obj
        print(f"listed {program}")

    total = len(targets)
    counts = {"already correct": 0, "moved": 0, "failed": 0, "not found": 0}
    start_time = time.time()

    def report_progress(checked):
        elapsed = time.time() - start_time
        remaining = total - checked
        eta = f", ~{elapsed / checked * remaining / 60:.0f} min left" if checked else ""
        summary = ", ".join(f"{k} {v}" for k, v in counts.items())
        print(f"[{checked}/{total} checked, {remaining} left{eta}] {summary}", flush=True)

    print(f"checking {total} objects")
    for checked, (drs_obj_id, program_id) in enumerate(targets.items(), start=1):
        if drs_obj_id not in current_objects:
            # may belong to a program we didn't or couldn't list
            response = client.request("GET", f"{drs_url}/objects/{drs_obj_id}")
            if response.status_code == 200:
                current_objects[drs_obj_id] = response.json()
        if drs_obj_id not in current_objects:
            counts["not found"] += 1
        elif current_objects[drs_obj_id].get("program") == program_id:
            # already moved, e.g. by an earlier run that stopped part way
            counts["already correct"] += 1
        else:
            current_object = current_objects[drs_obj_id]
            print(f"in {drs_obj_id}: changing {current_object.get("program")} to {program_id}")
            new_object = {**current_object, "program": program_id}
            response = client.request("POST", f"{drs_url}/objects", json=new_object)
            print(response.status_code, response.text)
            counts["moved" if response.status_code == 200 else "failed"] += 1
        if checked % 100 == 0:
            report_progress(checked)

    report_progress(total)
    if counts["failed"]:
        print("Some objects failed to move; re-run to retry them")


if __name__ == "__main__":
    main()
