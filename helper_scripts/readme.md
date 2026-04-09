# Ingest helper scripts

A collection of scripts for performing various data summary and update actions. Some of these may be directly useful, others are provided as examples based on a specific use case. 

`extract_drs.py` 

Given the output from a call to the `experiments` endpoint, collect all of the drs objects for those experiments. Written to go alongside the `reset_programs.py` script. 

`reset_programs.py`

A CanDIG instance renamed the program_id and updated clinical data. This script (along with `extract_drs`) updated the program_ids in the sequencing metadata without having to re-ingest all of the sequencing data. 

`get_ingested_files.py`

Returns a list of ingested sequencing files for the CanDIG instance. 