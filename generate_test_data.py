from git import Repo
import shutil
from clinical_etl import CSVConvert
import argparse
import os


def parse_args():
    parser = argparse.ArgumentParser(description="A script that ingests clinical data into Katsu")
    parser.add_argument("--output", help="Path to clone synth data repo.", required=True)
    return parser.parse_args()


def main(args):
    ingest_repo_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Cloning mohccn-synthetic-data repo into {args.output}")
    Repo.clone_from("https://github.com/CanDIG/mohccn-synthetic-data.git", args.output)
    print("Converting small_dataset_csvs to raw_data_map.json")
    CSVConvert.csv_convert(input_path=f"{args.output}/small_dataset_csv/raw_data",
                           manifest_file=f"{args.output}/small_dataset_csv/manifest.yml")
    print("moving files to tests directory")
    shutil.move(f"{args.output}/small_dataset_csv/raw_data_map.json",
                f"{ingest_repo_dir}/tests/small_dataset_clinical_ingest.json")
    shutil.move(f"{args.output}/small_dataset_csv/genomic.json",
                f"{ingest_repo_dir}/tests/small_dataset_genomic_ingest.json")
    print("Removing repo.")
    shutil.rmtree(args.output)


if __name__ == "__main__":
    args = parse_args()
    main(args)
