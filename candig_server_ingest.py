import sys
import argparse
import json
import os

# Create several files that can be run on the candig-server server. Copy the files over and then run `bash candigv1_ingest.sh.`

def main():
    parser = argparse.ArgumentParser(description="Creates ingest files for candig-server")
    parser.add_argument("--dataset", help="Dataset name", required=True)
    parser.add_argument("--input_file", help="The absolute path to the local data file", required=True)
    parser.add_argument("--patient_id", help="Column name for patient ID", required=True)
    parser.add_argument("--variant_file_id", help="Column name for variant file name or URL", required=True)
    parser.add_argument("--reference", help="Name of the reference sequence", required=True)
    parser.add_argument("--path", help="Optional: if provided, path to the directory containing the variant files")

    args = parser.parse_args()
    if args.path is None:
        args.path = ""

    input_data = {}
    with open(args.input_file) as input_file:
        lines = input_file.readlines()
        names = lines.pop(0).split(',')
        for name in names:
            input_data[name.strip()] = []
        while len(lines) > 0:
            linebits = lines.pop(0).split(',')
            for i in range(0,len(names)):
                input_data[names[i].strip()].append(linebits[i].strip())
    
    output_data = {
        "metadata": []
    }
    
    with open("temp/candigv1_ingest.sh", "w") as scriptfile:
        scriptfile.write("#!/usr/bin/env bash\n\nset -uo pipefail\n\n")
        scriptfile.write("# Execute this script with the path to the candig database as an argument.\n\n")
        scriptfile.write("DATABASE=$1\n\n")
        scriptfile.write('ingest\nif [ $? -ne 0 ]; then\n  echo "Is candig-ingest installed? https://candig-server.readthedocs.io/en/v1.5.0-alpha/datarepo.html#ingest"\n  exit 1\nfi\n\n')
        
        scriptfile.write("ingest candig-example-data/registry.db " + args.dataset + " candigv1_data.json\n\n")
                   
        for s in range(0,len(input_data[args.patient_id])):
            # write sample into output_data:
            sample = {
                "subject": {
                    "id": input_data[args.patient_id][s]
                },
                "Patient": {
                    "patientId": input_data[args.patient_id][s]
                }
            }
            output_data["metadata"].append(sample)
            
            # write add-variantset call into script
            cmd = ' '.join([
                'candig_repo add-variantset $DATABASE',
                args.dataset,
                input_data[args.patient_id][s],
                input_data[args.patient_id][s],
                os.path.join(args.path, input_data[args.variant_file_id][s]),
                '-R',
                args.reference
            ])
            scriptfile.write(cmd)
            scriptfile.write("\n")            

    with open("temp/candigv1_data.json", "w") as datafile:
        datafile.write(json.dumps(output_data, indent=4))

if __name__ == "__main__":
    main()
