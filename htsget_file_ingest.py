import argparse
import requests
import auth
import os
import re
import json
from htsget_methods import post_to_dataset, get_dataset_objects, post_objects


def collect_samples_for_genomic_id(genomic_id, file):
    type_parse = re.match(r"(.+)\.(vcf|bam|cram|sam|bcf)(\.gz)*", file)
    if type_parse is not None:
        if type_parse.group(2) == 'vcf' or type_parse.group(2) == 'bcf':
            type = 'variant'
            index = f"{file}.tbi"
        elif type_parse.group(2) == 'bam' or type_parse.group(2) == 'sam':
            type = 'read'
            index = f"{file}.bai"
        elif type_parse.group(2) == 'cram':
            type = 'read'
            index = f"{file}.crai"
        return [{
                "id": genomic_id,
                "file": os.path.basename(file),
                "index": os.path.basename(index),
                "type": type,
                "file_access": f"file://{os.path.abspath(file)}",
                "index_access": f"file://{os.path.abspath(index)}"
            }]


def main():
    parser = argparse.ArgumentParser(description="A script that ingests a sample vcf and its index into htsget.")

    parser.add_argument("--genomic_id", help="genomic sample id")
    parser.add_argument("--clinical_id", help="clinical sample registration id", required=False)
    parser.add_argument("--file", help="path to main file")
    parser.add_argument("--dataset", help="dataset name")
    parser.add_argument("--reference", help="optional: reference genome, either hg37 or hg38", required=False, default="hg38")
    parser.add_argument('--indexing', action="store_true", help="optional: force re-indexing")

    args = parser.parse_args()

    if os.getenv("CANDIG_URL") == "":
        raise Exception("CANDIG_URL environment variable is not set")

    token = auth.get_site_admin_token()

    objects_to_create = collect_samples_for_genomic_id(args.genomic_id, args.file)
    post_objects(args.genomic_id, objects_to_create, token, clinical_id=args.clinical_id, ref_genome=args.reference, force=args.indexing)
    post_to_dataset([args.genomic_id], args.dataset, token)
    response = get_dataset_objects(args.dataset, token)
    print(json.dumps(response, indent=4))


if __name__ == "__main__":
    main()
