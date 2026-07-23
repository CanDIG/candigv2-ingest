# Ingest helper scripts

A collection of scripts for performing various data summary and update actions. Some of these may be directly useful, others are provided as examples based on a specific use case.

## `delete_clinical_data_katsu.py`

Permanently delete only clinical data programs at a node. Can specify a list of specific programs to delete, a list of specific programs to exclude from deletion or if none specified will delete all clinical data at the node. This script will not delete any program registrations or ingested genomic/sequencing data. It is recommended you backup your clinical database before using in case you need to restore. 

```commandline
usage: delete_clinical_data_katsu.py [-h] --url URL [--exclude EXCLUDE] [--program-list PROGRAM_LIST]

Delete clinical data at a CanDIG node without deleting program registrations or genomic data.

options:
  -h, --help            show this help message and exit
  --url URL             Url of your candig instance
  --exclude EXCLUDE     Comma-delimited list of programs to exclude from the deletion, all other programs at the node will be deleted
  --program-list PROGRAM_LIST
                        Comma-delimited list of programs to delete
```

## `extract_drs.py`

Given the output from a call to the `biosamples` endpoint, collect all of the drs objects for those experiments. Written to go alongside the `reset_programs.py` script.

```commandline
usage: extract_drs.py [-h] [--file FILE] --url URL --token TOKEN --output OUTPUT

Extract all drs objects associated with the biosamples endpoint result.

options:
  -h, --help       show this help message and exit
  --file FILE      File with output of biosamples call
  --url URL        URL of the candig deployment you are retrieving data from
  --token TOKEN    site admin token for the candig deployment you are retrieving data from.
  --output OUTPUT  output file to write to
```

## `reset_programs.py`

A CanDIG instance renamed the program_id and updated clinical data. This script (along with `extract_drs`) updated the program_ids in the sequencing metadata without having to re-ingest all of the sequencing data.

```commandline
usage: reset_programs.py [-h] --input INPUT --corrected CORRECTED --url URL --token TOKEN

Given a list of drs objects returned from extract_drs.py and a list of updated mappings of samples to programs, update the drs objects to the correct programs.

options:
  -h, --help            show this help message and exit
  --input INPUT         File with output of extract_drs.py
  --corrected CORRECTED
                        CSV File with correct mapping of samples to programs. Columns should be: 
                        'Submitter Sample ID': the submitter sample id that links to all the objects that need to be moved, 
                        'Program ID': The program_id of the program that the objects should be moved to
  --url URL             URL of the candig deployment for which you want to update data
  --token TOKEN         site admin token for the candig deployment for which you want to update data
```

## `get_ingested_files.py`

Returns a list of ingested sequencing files for the CanDIG instance. Useful for checking whether all the files you expected were ingested properly succeeded.

```commandline
usage: get_ingested_files.py [-h] [--programs PROGRAMS] --url URL --token TOKEN [--output OUTPUT] [--save_api_output] [--read_api_output]

Output ingested sequencing files for specified programs into the output file candig_file_list.csv.

options:
  -h, --help           show this help message and exit
  --programs PROGRAMS  String of comma-separated programs ids; otherwise return all
  --url URL            URL of the candig deployment you are retrieving data from
  --token TOKEN        site admin token for the candig deployment you are retrieving data from.
  --output OUTPUT      output file to write to; default candig_files.csv
  --save_api_output    save api output for later calls; debugging
  --read_api_output    read api output from file candig_api_output.json rather than calling API
```

## `index_unindexed.sh`

Searches the database for variant files that are not fully indexed and creates a list of curl commands to index them again. Pipe the output of this script to a file and run the curl commands in batches if there are too many to do at once. 

> [!IMPORTANT]
> This script needs to be run on the VM where your CanDIG node is deployed as it needs direct access to the postgres docker container.

## `submit_program_registrations.py`

Submits all program registrations in a csv file, adding team members and program curators as specified. Only adds program registrations that do not already exist. Adds all listed team members and program curators to all programs, currently not possible to specify program specific team members/program curators.

```
usage: submit_program_registrations.py [-h] --input INPUT [--column-name COLUMN_NAME] --url URL --token TOKEN [--curators CURATORS] [--team-members TEAM_MEMBERS]

options:
  -h, --help            show this help message and exit
  --input INPUT         Csv file that has at least one column with the column header specified with the --column-name argument
  --column-name COLUMN_NAME
                        exact column name in the csv where the program id is specified. Default: 'program_id'
  --url URL             Full URL of the CanDIG node
  --token TOKEN         site admin or site curator token
  --curators CURATORS   comma delimited list of curators to add to each program
  --team-members TEAM_MEMBERS
                        comma delimited list of team members to add to each program
```

## `verified_analyses.py`

Checks the verification status of ingested sequencing files according to the output of a call to the `biosamples` endpoint. This lets you know whether the link to the location of each sequencing file is still valid or needs to be updated. 

> [!TIP]
> Need to make a call to the biosamples endpoint first with the samples/programs you want to check and save to a file, then specify its path as the --file argument.

```commandline
usage: verified_analyses.py [-h] [--file FILE] --url URL --token TOKEN --output OUTPUT

Get verified status of all analyses associated with the biosamples endpoint result.

options:
  -h, --help       show this help message and exit
  --file FILE      File with output of biosamples call
  --url URL        URL of the candig deployment you are retrieving data from
  --token TOKEN    site admin token for the candig deployment you are retrieving data from.
  --output OUTPUT  output file to write to
```
