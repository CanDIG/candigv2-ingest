from git import Repo
import shutil
from clinical_etl import CSVConvert


def main():
    print("Cloning mohccn-synthetic-data repo into tmp")
    Repo.clone_from("https://github.com/CanDIG/mohccn-synthetic-data.git", "tmp")
    print("Converting small_dataset_csvs to raw_data_map.json")
    CSVConvert.csv_convert(input_path="tmp/small_dataset_csv/raw_data",
                           manifest_file="tmp/small_dataset_csv/manifest.yml", minify=True,
                           index_output=False)
    print("moving files to tests directory")
    shutil.move("tmp/small_dataset_csv/raw_data_map.json", "tests/small_dataset_clinical_ingest.json")
    shutil.move("tmp/small_dataset_csv/genomic.json", "tests/small_dataset_genomic_ingest.json")
    print("Removing repo.")
    shutil.rmtree("tmp")


if __name__ == "__main__":
    main()
