import json
import sys
import pprint
import argparse
import requests as rq
import pandas as pd

def parse_args():
    parser = argparse.ArgumentParser(description="Output ingested sequencing files for specified programs into the output file candig_file_list.csv.")
    parser.add_argument('--programs', type=str,  help="String of comma-separated programs ids; otherwise return all")
    parser.add_argument('--url', type=str, required=True, help="URL of the candig deployment you are retrieving data from")
    parser.add_argument('--token', type=str, required=True, help="site admin token for the candig deployment you are retrieving data from.")
    parser.add_argument('--output', type=str, default="candig_files.csv", help="output file to write to; default candig_files.csv")
    parser.add_argument('--save_api_output', action="store_true", required=False, help="save api output for later calls; debugging")
    parser.add_argument('--read_api_output', action="store_true", required=False, help="read api output from file candig_api_output.json rather than calling API")

    args = parser.parse_args()
    return args


def get_genomic_data(token, url, save_api_output, read_api_output, program_list):
    experiments = {}

    if read_api_output:
        try:
            print("Reading API output from candig_api_output.json")
            with open("candig_api_output.json", "r") as f:
                experiments = json.load(f)
        except FileNotFoundError:
            print("API output file candig_api_output.json does not exist; try re-running script with --save_api_output and without --read_api_output")
            sys.exit(1)
    else:
        print(f"Fetching sequencing object data from CanDIG instance at {url}")
        headers = {"Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8"}
        response = rq.post(f"{url}/drs/ga4gh/drs/v1/experiments", headers=headers,
                        json={"program_ids": program_list})
        if response.status_code == 200:
            experiments = response.json()
            if save_api_output:
                with open("candig_api_output.json", "w") as f:
                        print("Writing API output to candig_api_output.json")
                        json.dump(experiments, f)
        elif response.status_code == 401:
            print(f"Response status code: {response.status_code}")
            print(f"Returned response:")
            pprint.pprint(response.json())
            print("Unauthorized to retrieve genomic data, try getting a new token and run the script again.")
            sys.exit()
        else:
            print(f"Response status code: {response.status_code}")
            print(f"Returned response:")
            pprint.pprint(response.json())
            print("WARN: Error retrieving genomic data.")

    return experiments

def get_completeness(experiment_objects, program_list):
    genomic_completeness_dict = {
        "program_id": [],
        "submitter_sample_id": [],
        "file_type" : [],
        "filenames" : []
    }
    for obj in experiment_objects:
        program = obj['program']
        if program in program_list:
            genomic_completeness_dict['program_id'].append(obj['program'])
            genomic_completeness_dict['submitter_sample_id'].append(obj['experiment_id'])
            for i in ['reads','expressions','variants']:
                files = obj[i]
                if len(files) > 0:
                    genomic_completeness_dict['file_type'].append(i)
                    genomic_completeness_dict['filenames'].append(obj[i][0])
                if len(files) > 1:
                    print(f"Warning: more than one {i} file found for {program}")
    # check if there are any programs in the list that we did not find in 
    # the experiment_objects
    missing_programs = list(set(program_list) - set(genomic_completeness_dict['program_id']))
    if len(missing_programs) > 0:
        print(f"Warning: no data found for following programs {missing_programs}")
    
    genomic_completeness_df = pd.DataFrame(genomic_completeness_dict)
    return genomic_completeness_df

def main():
    args = parse_args()
    program_list = args.programs
    program_list = [item.strip() for item in program_list.split(',')]
    print(f"Getting data for {program_list}")
    experiments = get_genomic_data(args.token, args.url, args.save_api_output, args.read_api_output, program_list)
    if len(experiments) > 0:
        completeness_df = get_completeness(experiments, program_list)
        completeness_df.to_csv("candig_file_list.csv")
    else: 
        print(f"No data found for any programs")
 
if __name__ == "__main__":
    main()
