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
    parser.add_argument("--output", help="Directory to temporarily clone the mohccn-synthetic-data repo.",
                        required=True)
    return parser.parse_args()


def main(args):
    ingest_repo_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Cloning mohccn-synthetic-data repo into {args.output}")
    repo = Repo.clone_from("https://github.com/CanDIG/mohccn-synthetic-data.git", args.output)
    # can be commented to check error behaviour
    repo.git.checkout('mshadbolt/invalid-data')

    try:
        if args.prefix:
            subprocess.run([f'python {args.output}/src/csv_to_ingest.py --size s --prefix {args.prefix}'],
                           shell=True, check=True)
            output_dir = f"{args.output}/custom_dataset_csv-{args.prefix}"
            with open(f'{output_dir}/raw_data_validation_results.json') as f:
                validation_results = json.load(f)
                if len(validation_results['validation_errors']) > 0:
                    raise ValidationError("Clinical etl conversion failed to create an ingestable json file, "
                                          "please check the errors in tests/clinical_data_validation_results.json and "
                                          "try again.")
        else:
            print("Converting small_dataset_csvs to raw_data_map.json")
            output_dir = f"{args.output}/small_dataset_csv"
            packets, errors = CSVConvert.csv_convert(input_path=f"{args.output}/small_dataset_csv/raw_data",
                                                     manifest_file=f"{args.output}/small_dataset_csv/manifest.yml")
            if errors:
                raise ValidationError("Clinical etl conversion failed to create an ingestable json file, "
                                      "please check the errors in tests/clinical_data_validation_results.json and "
                                      "try again.")
    except Exception as e:
        print(e)
        print(f"Moving validation results file to {ingest_repo_dir}/tests/small_dataset_clinical_ingest_validation_results.json.")
        shutil.move(f"{output_dir}/raw_data_validation_results.json",
                    f"{ingest_repo_dir}/tests/small_dataset_clinical_ingest_validation_results.json")
        print("Removing repo.")
        shutil.rmtree(args.output)
        sys.exit(0)

    print("Ingestable JSON successfully created, moving output json files to tests directory")
    shutil.move(f"{output_dir}/raw_data_map.json",
                f"{ingest_repo_dir}/tests/small_dataset_clinical_ingest.json")

    shutil.move(f"{output_dir}/genomic.json",
                f"{ingest_repo_dir}/tests/small_dataset_genomic_ingest.json")
    print("Removing repo.")
    shutil.rmtree(args.output)


if __name__ == "__main__":
    args = parse_args()
    main(args)
