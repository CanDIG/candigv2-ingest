import argparse
import requests
import auth


def post_object(sample_id, file_dir, htsget_url, token):
	headers = {"Authorization": f"Bearer {token}"}
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
    response = requests.post(url, json=obj, headers=headers)
    obj["access_methods"][0]["access_url"]["url"] += ".tbi"
    obj["id"] += ".tbi"
    obj["name"] += ".tbi"
    obj["self_uri"] += ".tbi"

    response = requests.post(url, json=obj, headers=headers)

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
    
    response = requests.post(url, json=obj, headers=headers)

    return response


def post_to_dataset(sample_id, dataset, htsget_url, token):
	headers = {"Authorization": f"Bearer {token}"}
    obj = {
        "id": dataset,
        "drsobjects": [
            f"drs://localhost/{sample_id}"
        ]
    }
    url = f"{htsget_url}/ga4gh/drs/v1/datasets"
    response = requests.post(url, json=obj, headers=headers)


def main():
    parser = argparse.ArgumentParser(description="A script that ingests a sample vcf and its index into htsget.")

    parser.add_argument("sample", help="sample id.")
    parser.add_argument("dir", help="file directory.")
    parser.add_argument("server_url", help="URL of the htsget server.")
    parser.add_argument("dataset", help="dataset name")

    args = parser.parse_args()
	token = auth.get_site_admin_token()

    post_object(args.sample, args.dir, args.server_url, token)
    post_to_dataset(args.sample, args.dataset, args.server_url, token)


if __name__ == "__main__":
    main()
