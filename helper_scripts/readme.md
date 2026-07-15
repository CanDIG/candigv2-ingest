# Ingest helper scripts

A collection of scripts for performing various data summary and update actions. Some of these may be directly useful, others are provided as examples based on a specific use case.

`delete_clinical_data_katsu.py`

Delete only clinical data from all/specified programs at a node.

`extract_drs.py`

Given the output from a call to the `experiments` endpoint, collect all of the drs objects for those experiments. Written to go alongside the `reset_programs.py` script.

`reset_programs.py`

A CanDIG instance renamed the program_id and updated clinical data. This script (along with `extract_drs`) updated the program_ids in the sequencing metadata without having to re-ingest all of the sequencing data.

`get_ingested_files.py`

Returns a list of ingested sequencing files for the CanDIG instance.

`submit_program_registrations.py`

Submits all program registrations in a csv file, adding team members and program curators as specified. Only adds
program registrations that do not already exist.

`index_unindexed.sh`

Searches the database for variant files that are not fully indexed and creates a list of curl commands to index them again. Pipe the output of this script to a file and run the curl commands in batches if there are too many to do at once. 

> [!IMPORTANT]
> This script needs to be run on the VM where your CanDIG node is deployed as it needs direct access to the postgres docker container.
