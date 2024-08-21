from git import Repo
import shutil
from clinical_etl import CSVConvert
from clinical_etl.schema import ValidationError
import argparse
import os
import sys
import subprocess
import json


def parse_args():
    parser = argparse.ArgumentParser(description="A script that copies and converts data from mohccn-synthetic-data for "
                                                 "ingest into CanDIG platform.")
    parser.add_argument("--prefix", help="optional prefix to apply to all identifiers")
    parser.add_argument("--tmp", help="Directory to temporarily clone the mohccn-synthetic-data repo.",
                        default="tmp-data")
    return parser.parse_args()


def main(args):
    ingest_repo_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(args.tmp):
        yes = ['yes', 'y', 'ye', '']
        no = ['no', 'n']
        response = input(f"Specified directory {args.tmp}, ok to delete? (yes/no)")
        if response.lower() in yes:
            shutil.rmtree(args.tmp)
        else:
            print("Cannot clone repo until --tmp directory is removed. Remove manually or specify an alternate --tmp "
                  "destination.")
            sys.exit()
    print(f"Cloning mohccn-synthetic-data repo into {args.tmp}")
    synth_repo = Repo.clone_from("https://github.com/CanDIG/mohccn-synthetic-data.git", args.tmp)
    # TODO: remove next line when changes are merged into develop
    synth_repo.git.checkout('mshadbolt/factory-boy-synth-data')

    try:
        if args.prefix:

            process = subprocess.run([f'python {args.tmp}/src/csv_to_ingest.py --size s --prefix {args.prefix}'],
                                     shell=True, check=True, capture_output=True)
            output_dir = f"{args.tmp}/custom_dataset_csv-{args.prefix}"

            with open(f'{output_dir}/raw_data_validation_results.json') as f:
                validation_results = json.load(f)
                if len(validation_results['validation_errors']) > 0:
                    raise ValidationError("Clinical etl conversion failed to create an ingestable json file, "
                                          "please check the errors in tests/clinical_data_validation_results.json and "
                                          "try again.")
        else:
            print("Converting small_dataset_csvs to small_dataset_clinical_ingest.json")
            output_dir = f"{args.tmp}/small_dataset_csv"
            process = subprocess.run([f'python {args.tmp}/src/csv_to_ingest.py --size s'],
                                     shell=True, check=True, capture_output=True)
            with open(f"{args.tmp}/small_dataset_csv/raw_data_validation_results.json") as f:
                errors = json.load(f)['validation_errors']
            if len(errors) > 0:
                raise ValidationError("Clinical etl conversion failed to create an ingestable json file, "
                                      "please check the errors in tests/clinical_data_validation_results.json and "
                                      "try again.")
    except ValidationError as e:
        print(e)
        print(f"Moving validation results file to {ingest_repo_dir}/tests/small_dataset_clinical_ingest_validation_results.json.")
        shutil.move(f"{output_dir}/raw_data_validation_results.json",
                    f"{ingest_repo_dir}/tests/small_dataset_clinical_ingest_validation_results.json")
        print("Removing repo.")
        shutil.rmtree(args.tmp)
        sys.exit(0)

    print("Ingestable JSON successfully created, moving output json files to tests directory")
    shutil.move(f"{output_dir}/raw_data_map.json",
                f"{ingest_repo_dir}/tests/small_dataset_clinical_ingest.json")

    shutil.move(f"{output_dir}/genomic.json",
                f"{ingest_repo_dir}/tests/small_dataset_genomic_ingest.json")
    print("Removing repo.")
    shutil.rmtree(args.tmp)

    programs = {}
    with open(f'{ingest_repo_dir}/tests/small_dataset_clinical_ingest.json', "r") as f:
        full_json = json.load(f)
    # split ingest files by program
    for donor in full_json['donors']:
        try:
            programs[donor['program_id']]['donors'].append(donor)
        except KeyError as e:
            programs[donor['program_id']] = {
                "openapi_url": "https://raw.githubusercontent.com/CanDIG/katsu/model_3/chord_metadata_service/mohpackets/docs/schema.yml",
                "schema_class": "MoHSchemaV3",
                "donors": [donor]}
    for program, content in programs.items():
        with open(f"{ingest_repo_dir}/tests/{program}.json", "w+") as f:
            json.dump(content, f)


if __name__ == "__main__":
    args = parse_args()
    main(args)
