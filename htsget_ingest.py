import argparse

from authx.auth import get_site_admin_token, is_action_allowed_for_program, create_service_token, get_s3_url
from auth import get_program
import os
import re
import json
import requests
import sys
from urllib.parse import urlparse
from clinical_etl.schema import openapi_to_jsonschema
import jsonschema
from candigv2_logging.logging import CanDIGLogger


logger = CanDIGLogger(__file__)


CANDIG_URL = os.getenv("CANDIG_URL", "")
HTSGET_URL = os.getenv("HTSGET_URL", f"{CANDIG_URL}/genomics")
# TAKUAN_URL = os.getenv("RNAGET_URL", f"{CANDIG_URL}/rnaget")
DRS_HOST_URL = "drs://" + CANDIG_URL.replace(f"{urlparse(CANDIG_URL).scheme}://","") + "/genomics"
KATSU_URL = os.environ.get("KATSU_URL")
IS_TESTING = os.getenv("IS_TESTING", False)


def link_genomic_data(analysis, do_not_index=False):
    url = f"{HTSGET_URL}/ga4gh/drs/v1/objects"
    result = {
        "errors": []
    }

    # Use service token to authenticate this with htsget
    headers = {}
    if not IS_TESTING:
        headers = {
            "X-Service-Token": create_service_token(),
            "Content-Type": "application/json"
        }

    analysis_type = analysis["metadata"]["analysis_type"]

    # get the master analysis object, or create it:
    analysis_drs_obj = {}
    response = requests.get(f"{url}/{analysis['analysis_id']}", headers=headers)
    if response.status_code == 200:
        analysis_drs_obj = response.json()
    analysis_drs_obj["id"] = analysis["analysis_id"]
    analysis_drs_obj["name"] = analysis["analysis_id"]
    analysis_drs_obj["description"] = analysis_type
    analysis_drs_obj["program"] = analysis["program_id"]
    analysis_drs_obj["reference_genome"] = analysis["metadata"]["reference"]
    analysis_drs_obj["version"] = "v1"
    analysis_drs_obj["metadata"] = analysis["metadata"]
    if "contents" not in analysis_drs_obj:
        analysis_drs_obj["contents"] = []

    # add AnalysisDataDrsObject to contents
    response = add_file_drs_object(analysis_drs_obj, analysis["main"], "analysis", headers)
    result["name"] = response["name"]
    result["id"] = response["id"]
    if "error" in response:
        result["errors"].append(response["error"])
        return result

    if "index" in analysis:
        # add AnalysisIndexDrsObject to contents
        response = add_file_drs_object(analysis_drs_obj, analysis["index"], "index", headers)
        if "error" in response:
            result["errors"].append(response["error"])
            return result

    for clin_sample in analysis["samples"]:
        # for each analysis in the samples, get the ExperimentDrsObject
        response = requests.get(f"{url}/{clin_sample['experiment_id']}", headers=headers)
        if response.status_code == 200:
            experiment_drs_obj = response.json()
        else:
            result["errors"].append(f"couldn't find experiment drs object {clin_sample['experiment_id']}: {response.status_code} {response.text}")
            return result

        # add the AnalysisDrsObject to its contents, if it's not already there:
        not_found = True
        if len(experiment_drs_obj["contents"]) > 0:
            for obj in experiment_drs_obj["contents"]:
                if obj["name"] == analysis["analysis_id"]:
                    not_found = False
        if not_found:
            contents_obj = {
                "name": analysis["analysis_id"],
                "id": analysis["analysis_id"],
                "drs_uri": [f"{DRS_HOST_URL}/{analysis['analysis_id']}"]
            }
            experiment_drs_obj["contents"].append(contents_obj)

        # update the experiment_drs_object in the database:
        response = requests.post(f"{url}", json=experiment_drs_obj, headers=headers)
        if response.status_code != 200:
            result["errors"].append(f"error updating experiment drs object {experiment_drs_obj['id']}: {response.status_code} {response.text}")
            return result

        # then add the experiment to the AnalysisDrsObject's contents, if it's not already there:
        contents_obj = {
            "name": experiment_drs_obj["name"],
            "id": clin_sample["analysis_sample_id"],
            "drs_uri": [f"{DRS_HOST_URL}/{clin_sample['experiment_id']}"]
        }
        not_found = True
        if len(analysis_drs_obj["contents"]) > 0:
            for i in range(0, len(analysis_drs_obj["contents"])):
                if analysis_drs_obj["contents"][i]["name"] == clin_sample["experiment_id"]:
                    not_found = False
                    analysis_drs_obj["contents"][i] = contents_obj
                    break
        if not_found:
            analysis_drs_obj["contents"].append(contents_obj)

    # finally, post the analysis_drs_object
    response = requests.post(url, json=analysis_drs_obj, headers=headers)
    if response.status_code != 200:
        result["errors"].append(f"error posting analysis drs object {analysis_drs_obj['id']}: {response.status_code} {response.text}")
        return result
    else:
        result["sample"] = f"connected submitter_sample_id {contents_obj["name"]} to analysis_sample_id {contents_obj["id"]}"

    # send the data to the downstream service: either htsget or takuan
    if analysis_drs_obj["metadata"]["analysis_type"] == "sequence_annotation":
        if "analysis_attribute" in analysis_drs_obj["metadata"] and analysis_drs_obj["metadata"]["analysis_attribute"]["subtype"] == "expression_count":
            pass
#             # first, create experiment in Takuan:
#             experiment_json = {
#                 "experiment_result_id": experiment_drs_obj["id"],
#                 "assembly_id": "GCA_000001405.27",
#                 "assembly_name": "GRCh38",
#                 "extra_properties": {}
#             }
#             response = requests.post(f"{TAKUAN_URL}/experiment", json=experiment_json, headers=headers)
#             logger.debug(f"takuan experiment post {response.status_code}, {response.text}")
#
#             # ingest matrix
#             response = requests.get(f"{HTSGET_URL}/ga4gh/drs/v1/objects/{analysis["main"]["name"]}/download", headers=headers)
#             if response.status_code == 200:
#                 raw_tsv_data = response.text.strip()
#                 lines = raw_tsv_data.split("\n")
#                 titles = lines.pop(0).split("\t")
#                 tsv_dict = {}
#                 for line in lines:
#                     values = line.split("\t")
#                     for v in range(len(values)):
#                         if titles[v] not in tsv_dict:
#                             tsv_dict[titles[v]] = []
#                         tsv_dict[titles[v]].append(values[v])
#
#                 input_dict = {
#                     "gene_id": tsv_dict['gene_id'],
#                     "abundance": tsv_dict['TPM'],
#                     "counts": tsv_dict['expected_count'],
#                     "length": tsv_dict['length']
#                 }
#                 titles = list(input_dict.keys())
#                 tsv_string_data =  "\t".join(titles)
#                 for i in range(len(input_dict[titles[0]])):
#                     tsv_string_data += "\n"
#                     for key in input_dict.keys():
#                         tsv_string_data += input_dict[key][i] + "\t"
#                 tsv_string_data = tsv_string_data.strip()
#                 string_data = bytes(tsv_string_data, "utf-8")
#                 response = requests.post(
#                     f"{TAKUAN_URL}/experiment/{experiment_drs_obj["id"]}/ingest/single?sample_id={experiment_drs_obj["id"]}&norm_type=tpm",
#                     data=dict(data=string_data),
#                 )
#                 if response.status_code != 200:
#                     result["errors"].append(f"takuan: {response.status_code} {response.text}")
#             else:
#                 result["errors"].append(f"could not load analysis: {response.text}")
    else:
        # send it to htsget
        # verify that the genomic file exists and is readable
        verify_url = f"{HTSGET_URL}/htsget/v1/{analysis_drs_obj['id']}/verify"

        response = requests.get(verify_url, headers=headers)
        if response.status_code != 200:
            result["errors"].append(f"could not verify analysis: {response.text}")
            return result
        elif not response.json()['result']:
            result["errors"].append(f"could not verify analysis: {response.json()['message']}")
            return result
        else:
            # flag the analysis_drs_object for indexing:
            url =f"{HTSGET_URL}/htsget/v1/{analysis_drs_obj['id']}/index"
            result["to_index"] = [url]
    return result


def add_file_drs_object(analysis_drs_obj, file, type, headers):
    url = f"{HTSGET_URL}/ga4gh/drs/v1/objects"
    obj = {
        "access_methods": [],
        "id": file['name'],
        "name": file['name'],
        "description": type,
        "program": analysis_drs_obj["program"],
        "version": "v1"
    }
    contents_obj = {
        "name": file["name"],
        "id": type,
        "drs_uri": [f"{DRS_HOST_URL}/{file['name']}"]
    }
    access_method = get_access_method(file["access_method"])
    if access_method is not None:
        if "message" in access_method:
            contents_obj["error"] = access_method["message"]
            return contents_obj
        obj["access_methods"].append(access_method)

    # is this file already in the master object? If so, replace it:
    not_found = True
    if len(analysis_drs_obj["contents"]) > 0:
        for i in range(0, len(analysis_drs_obj["contents"])):
            if analysis_drs_obj["contents"][i]["name"] == file["name"]:
                analysis_drs_obj["contents"][i] = contents_obj
                not_found = False
                break
    if not_found:
        analysis_drs_obj["contents"].append(contents_obj)
    response = requests.post(url, json=obj, headers=headers)
    if response.status_code > 200:
        contents_obj["error"] =  f"error creating file drs object: {response.status_code} {response.text}"
    return contents_obj


def get_access_method(url):
    if url.startswith("file"):
        return {
            "type": "file",
            "access_url": {
                "url": url
            }
        }
    try:
        result = parse_s3_url(url)
    except Exception as e:
        return {
            "message": str(e)
        }
    return {
        "type": "s3",
        "access_id": url
    }


def parse_s3_url(url):
    """
    Parse a url into s3 components
    """
    s3_url_parse = re.match(r"((https*|s3):\/\/(.+?))\/(.+)", url)
    if s3_url_parse is not None:
        if s3_url_parse.group(2) == "s3":
            raise Exception(f"Incorrect URL format {url}. S3 URLs should be in the form http(s)://endpoint-url/bucket-name/object. If your object is stored at AWS S3, you can find more information about endpoint URLs at https://docs.aws.amazon.com/general/latest/gr/rande.html")
        endpoint = s3_url_parse.group(1)
        bucket_parse = re.match(r"(.+?)\/(.+)", s3_url_parse.group(4))
        if bucket_parse is not None:
            data = {
                "endpoint": endpoint,
                "bucket": bucket_parse.group(1),
                "object": bucket_parse.group(2)
            }
            # check existence of credential for this:
            object = data["object"].split("?public=")
            data["object"] = object[0]
            if len(object) > 1:
                data["object"] = object[0]
                response, status_code = get_s3_url(s3_endpoint=data["endpoint"], bucket=data["bucket"], object_id=data["object"], access_key=None, secret_key=None, region=None, public=True)
            else:
                response, status_code = get_s3_url(s3_endpoint=data["endpoint"], bucket=data["bucket"], object_id=data["object"], access_key=None, secret_key=None, region=None, public=False)

            if status_code == 500:
                    raise Exception(response["error"])
            return data
        raise Exception(f"S3 URI {url} does not contain a bucket name")
    raise Exception(f"URI {url} cannot be parsed as an S3-style URI")


def htsget_ingest(ingest_json, do_not_index=False, results_path=None, result_dict=None):
    result = {
        "results": []
    }
    url = f"{HTSGET_URL}/ga4gh/drs/v1/objects"
    # Use service token to authenticate this with htsget
    headers = {}
    if not IS_TESTING:
        headers = {
            "X-Service-Token": create_service_token(),
            "Content-Type": "application/json"
        }

    program_ids = set()
    to_index = []
    status_code = 200
    result["errors"] = []
    for experiment in ingest_json["experiments"]:
        experiment_drs_obj = {
            "id": experiment["experiment_id"],
            "name": experiment["submitter_sample_id"],
            "description": experiment["metadata"]["library_strategy"].lower(),
            "program": experiment["program_id"],
            "version": "v1",
            "metadata": experiment["metadata"],
            "contents": []
        }
        response = requests.post(f"{url}", json=experiment_drs_obj, headers=headers)
        if response.status_code != 200:
            result["errors"].append(f"error creating experiment drs object {experiment_drs_obj['id']}: {response.status_code} {response.text}")

    for analysis in ingest_json["analyses"]:
        if result_dict is not None and analysis["program_id"] not in result_dict:
            result_dict[analysis["program_id"]] = result

        logger.debug(f"Ingesting {analysis['analysis_id']}, do_not_index = {do_not_index}")
        program_ids.add(analysis["program_id"])
        result["results"].append(f"processing analysis {analysis["analysis_id"]}...")

        if results_path is not None and result_dict is not None:
            with open(results_path, "w") as f:
                json.dump(result_dict, f)

        # create the corresponding DRS objects
        if "samples" not in analysis or len(analysis["samples"]) == 0:
            result["results"][-1] = f"error processing analysis {analysis["analysis_id"]}: No samples were specified"
            break
        response = link_genomic_data(analysis, do_not_index)

        # remove the temporary "processing..." message
        result["results"].pop()

        if len(response["errors"]) > 0:
            for err in response["errors"]:
                if "403" in err:
                    status_code = 403
                    break
                result["results"].append(f"error processing {response["id"]} {response["name"]} in experiment {analysis["analysis_id"]}: {err}")
        else:
            result["results"].append(f"processed {response["id"]} {response["name"]} for experiment {analysis["analysis_id"]}")
            if "sample" in response:
                result["results"].append(response["sample"])

        if "to_index" in response:
            to_index.extend(response.pop("to_index"))

    # Use service token to authenticate this with htsget
    headers = {}
    if not IS_TESTING:
        headers = {
            "X-Service-Token": create_service_token(),
            "Content-Type": "application/json"
        }

    # send off index calls
    if not do_not_index:
        for url in to_index:
            response = requests.get(url, headers=headers)

    # update completeness stats for program_ids with created experiments
    statistics = {}
    for program_id in program_ids:
        url = f"{HTSGET_URL}/htsget/v1/experiments"
        response = requests.get(url, headers=headers, params={"program": program_id})
        if response.status_code == 200:
            for experiment in response.json():
                logger.debug(experiment)
                if program_id not in statistics:
                    statistics[program_id] = { 'genomes': 0, 'transcriptomes': 0, 'all': 0 }
                if len(experiment['genomes']) > 0 and len(experiment['transcriptomes']) > 0:
                    statistics[program_id]['all'] += 1
                if len(experiment['genomes']) > 0:
                    statistics[program_id]['genomes'] += 1
                if len(experiment['transcriptomes']) > 0:
                    statistics[program_id]['transcriptomes'] += 1
        else:
            result["errors"].append(f"Could not collect completeness stats for program: {response.text}")

    for program_id in statistics:
        # get the program
        url = f"{HTSGET_URL}/ga4gh/drs/v1/programs"
        response = requests.get(f"{url}/{program_id}", headers=headers)
        if response.status_code == 200:
            program = response.json()
            program["statistics"] = statistics[program_id]
            response = requests.post(url, headers=headers, json=program)
            if response.status_code != 200:
                result["errors"].append(f"Could not add statistics for program: {response.text}")
        else:
            result["errors"].append(f"Could not add statistics for program: {response.text}")

    if len(result["errors"]) == 0:
        result.pop("errors")

    return result, status_code


def check_genomic_data(dataset, token):
    with open("ingest_openapi.yaml") as f:
        openapi_text = f.read()
        experiment_schema = openapi_to_jsonschema(openapi_text, "Experiment")
        analysis_schema = openapi_to_jsonschema(openapi_text, "Analysis")
    result = {
        "errors": {},
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    # list samples by program
    by_program = {}
    for experiment in dataset["experiments"]:
        program_id = experiment["program_id"]
        if program_id not in by_program:
            by_program[program_id] = {"experiments": [], "analyses": []}
        by_program[program_id]["experiments"].append(experiment)
    for analysis in dataset["analyses"]:
        program_id = analysis["program_id"]
        if program_id not in by_program:
            by_program[program_id] = {"experiments": [], "analyses": []}
        by_program[program_id]["analyses"].append(analysis)


    for program_id in by_program.keys():
        if program_id not in result["errors"]:
            result["errors"][program_id] = []
        response, status_code = get_program(program_id)
        if status_code > 300:
            result["errors"][program_id].append({"not found": "No program authorization exists"})
        elif not is_action_allowed_for_program(token, method="POST", path="/ga4gh/drs/v1/objects", program=program_id):
            result["errors"][program_id].append({"unauthorized": "user is not allowed to ingest to program"})
            continue
        # look for program in katsu
        response = requests.get(f"{KATSU_URL}/v3/authorized/programs", params={"program_id": program_id}, headers=headers)
        if response.status_code == 200:
            if "items" in response.json() and len(response.json()["items"]) == 0:
                result["errors"][program_id].append({"no such program": "program does not exist in clinical data"})
                continue

        # get all sample_registrations for this program
        samples_in_program = []
        response = requests.get(f"{KATSU_URL}/v3/authorized/sample_registrations", params={"program_id": program_id, "page_size": 10000000}, headers=headers)
        if response.status_code == 200:
            samples_in_program.extend(list(map(lambda x: x["submitter_sample_id"], response.json()["items"])))
        for experiment in by_program[program_id]["experiments"]:
            sample_errors = []
            # validate the json
            for error in jsonschema.Draft202012Validator(experiment_schema).iter_errors(experiment):
                sample_errors.extend(f"{' > '.join(error.path)}: {error.message}")
            if len(sample_errors) > 0:
                continue
            # check to see if the samples exist in katsu
            if experiment["submitter_sample_id"] not in samples_in_program:
                sample_errors.append({"no such sample": f"sample {experiment['submitter_sample_id']} does not exist in clinical data {samples_in_program}"})
            if len(sample_errors) > 0:
                result["errors"][program_id].append({experiment["experiment_id"]: sample_errors})
        for analysis in by_program[program_id]["analyses"]:
            sample_errors = []
            # validate the json
            if analysis["analysis_id"] == analysis["main"]["name"]:
                sample_errors = f"Experiment {analysis['analysis_id']} cannot have the same name as one of its files."
            if "index" in analysis and analysis["analysis_id"] == analysis["index"]["name"]:
                sample_errors = f"Experiment {analysis['analysis_id']} cannot have the same name as one of its files."
            else:
                for error in jsonschema.Draft202012Validator(analysis_schema).iter_errors(analysis):
                    sample_errors.extend(f"{' > '.join(error.path)}: {error.message}")
            if len(sample_errors) > 0:
                result["errors"][program_id].append({analysis["analysis_id"]: sample_errors})
        if len(result["errors"][program_id]) == 0:
            result["errors"].pop(program_id)
    if len(result["errors"]) == 0:
        return by_program, 200
    return result, 400


def delete_program(program_id, token):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{HTSGET_URL}/ga4gh/drs/v1/programs/{program_id}"

    return requests.delete(url, headers=headers)


def main():
    parser = argparse.ArgumentParser(description="A script that ingests genomic data into htsget.")
    parser.add_argument("--samplefile", required=True,
                        help="A file specifying the location and sample linkages for one or more genomic files")

    args = parser.parse_args()

    genomic_input = []
    if args.samplefile:
        with open(args.samplefile) as f:
            genomic_input = json.loads(f.read())
    if len(genomic_input) == 0:
        return "No samples to ingest"
    token = get_site_admin_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    result, status_code = check_genomic_data(genomic_input, token)
    if status_code == 200:
        result, status_code = htsget_ingest(result)
    print(json.dumps(result, indent=4))

if __name__ == "__main__":
    main()
