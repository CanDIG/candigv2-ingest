import argparse
import requests


def post_object(sample_id, file_dir, htsget_url):
    obj = {
            "access_methods": [
              {
                "access_url": {
                  "url": f"file:///{file_dir}/{sample_id}.vcf.gz"
                },
                "type": "file"
              }
            ],
            "id": f"{sample_id}.vcf.gz",
            "name": f"{sample_id}.vcf.gz",
            "self_uri": f"drs://localhost/{sample_id}.vcf.gz",
            "version": "v1"
          }
    url = f"{htsget_url}/ga4gh/drs/v1/objects"
    response = requests.post(url, json=obj)
    obj["access_methods"][0]["access_url"]["url"] += ".tbi"
    obj["id"] += ".tbi"
    obj["name"] += ".tbi"
    obj["self_uri"] += ".tbi"

    response = requests.post(url, json=obj)

    obj = {
        "contents": [
          {
            "drs_uri": [
              f"drs://localhost/{sample_id}.vcf.gz"
            ],
            "name": f"{sample_id}.vcf.gz",
            "id": "variant"
          },
          {
            "drs_uri": [
              f"drs://localhost/{sample_id}.vcf.gz.tbi"
            ],
            "name": f"{sample_id}.vcf.gz.tbi",
            "id": "index"
          }
        ],
        "id": sample_id,
        "name": sample_id,
        "self_uri": f"drs://localhost/{sample_id}",
        "version": "v1"
    }
    
    response = requests.post(url, json=obj)

    return response


def post_to_dataset(sample_id, dataset, htsget_url):
    obj = {
        "id": dataset,
        "drsobjects": [
            f"drs://localhost/{sample_id}"
        ]
    }
    url = f"{htsget_url}/ga4gh/drs/v1/datasets"
    response = requests.post(url, json=obj)


def main():
    parser = argparse.ArgumentParser(description="A script that ingests a sample vcf and its index into htsget.")

    parser.add_argument("sample", help="sample id.")
    parser.add_argument("dir", help="file directory.")
    parser.add_argument("server_url", help="URL of the htsget server.")
    parser.add_argument("dataset", help="dataset name")

    args = parser.parse_args()
    sample = args.sample
    file_dir = args.dir
    server_url = args.server_url
    dataset = args.dataset

    post_object(sample, file_dir, server_url)
    post_to_dataset(sample, dataset, server_url)


if __name__ == "__main__":
    main()
