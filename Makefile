#!make

# import global variables
# NOTE: if your CANDIG_HOME is in a different location, 
# set the environment variable or set it when calling make
CANDIG_HOME ?= ../CanDIGv2
env ?= $(CANDIG_HOME)/.env

include $(env)
export $(shell sed 's/=.*//' $(env))

SHELL = bash
DIR = $(PWD)
KATSU = $(shell docker ps --format "{{.Names}}" | grep "chord-metadata")
HTSGET=$(shell docker ps --format "{{.Names}}" | grep "htsget")
CANDIG_SERVER=$(shell docker ps --format "{{.Names}}" | grep "candig-server")
# either opa container will work
OPA=$(shell docker ps --format "{{.Names}}" | grep -m 1 "opa")

DATASET="mcode-synthetic"
DATASET2="subset-data"

.PHONY: all
all: copy-samples opa.ready katsu.ready candig_server.ready second-set
	source ./ingest.sh $(DATASET)
	
.PHONY: copy-samples
copy-samples: samples/*.gz.tbi
	docker cp samples $(KATSU):samples
	docker cp samples $(HTSGET):samples
	docker cp samples $(CANDIG_SERVER):/samples

samples/*.vcf: | /samples
	@echo "generating..."
	$(shell cd samples; python ../generate_genomic.py)

samples/*.gz.tbi: | /samples
ifeq (, $(shell which bgzip))
$(error "bgzip is part of htslib; htslib is required to manage variant files: installation instructions are at https://www.htslib.org/download/")
endif
$(foreach F, $(wildcard samples/*.vcf), $(shell bgzip $(F); tabix $(F).gz))

/samples:
	@mkdir -p $(DIR)/samples

clinical_ETL.ready:
	git submodule update --init
	@pip install -r clinical_ETL/requirements.txt
	@pip install -r requirements.txt
	@touch clinical_ETL.ready

reference.ready: hs37d5.fa.gz hs37d5.fa.gz.gzi
	@echo "loading reference data"
	docker cp hs37d5.fa.gz $(CANDIG_SERVER):/app/candig-server
	docker cp hs37d5.fa.gz.gzi $(CANDIG_SERVER):/app/candig-server
	docker exec $(CANDIG_SERVER) candig_repo add-referenceset candig-example-data/registry.db hs37d5.fa.gz \
		--description "NCBI37 assembly of the human genome" \
		--species '{"termId": "NCBI:9606", "term": "Homo sapiens"}' \
		--name hs37d5 \
		--sourceUri http://ftp.1000genomes.ebi.ac.uk/vol1/ftp/technical/reference/phase2_reference_assembly_sequence/hs37d5.fa.gz
	@touch reference.ready

hs37d5.fa.gz: 
	curl http://ftp.1000genomes.ebi.ac.uk/vol1/ftp/technical/reference/phase2_reference_assembly_sequence/hs37d5.fa.gz --output hs37d5.fa.gz

hs37d5.fa.gz.gzi:
	curl http://ftp.1000genomes.ebi.ac.uk/vol1/ftp/technical/reference/phase2_reference_assembly_sequence/hs37d5.fa.gz.gzi --output hs37d5.fa.gz.gzi

katsu.ready: | clinical_ETL.ready
	python clinical_ETL/CSVConvert.py --input Synthetic_Clinical+Genomic_data/Synthetic_Clinical_Data_2 --mapping mappings/synthetic2mcode/manifest.yml
	docker cp Synthetic_Clinical+Genomic_data/Synthetic_Clinical_Data_2_map.json $(KATSU):Synthetic_Clinical_Data_2_map_mcode.json
	python katsu_ingest.py $(DATASET) $(DATASET) $(DATASET) $(CHORD_METADATA_INGEST_URL) /Synthetic_Clinical_Data_2_map_mcode.json mcodepacket
	@touch katsu.ready

candig_server.ready: | clinical_ETL.ready reference.ready
	python clinical_ETL/CSVConvert.py --input Synthetic_Clinical+Genomic_data/Synthetic_Clinical_Data_2 --mapping mappings/synthetic2candigv1/manifest.yml
	docker cp Synthetic_Clinical+Genomic_data/Synthetic_Clinical_Data_2_map.json $(CANDIG_SERVER):Synthetic_Clinical_Data_2_map_candigv1.json
	docker exec $(CANDIG_SERVER) ingest candig-example-data/registry.db $(DATASET) /Synthetic_Clinical_Data_2_map_candigv1.json
	docker restart $(CANDIG_SERVER)
	@touch candig_server.ready

opa.ready: 
	python opa_init.py $(shell cat $(CANDIG_HOME)/tmp/secrets/keycloak-test-user) $(DATASET) \
		$(OPA_URL) $(CANDIG_OPA_SECRET) > access.json
	docker cp access.json $(OPA):/app/permissions_engine/access.json
	@touch opa.ready

.PHONY: second-set
second-set:
	python clinical_ETL/CSVConvert.py --input Synthetic_Clinical+Genomic_data/Subset_data --mapping mappings/synthetic2mcode/manifest.yml
	docker cp Synthetic_Clinical+Genomic_data/Subset_data_map.json $(KATSU):Subset_data_map_mcode.json
	python katsu_ingest.py $(DATASET2) $(DATASET2) $(DATASET2) $(CHORD_METADATA_INGEST_URL) /Subset_data_map_mcode.json mcodepacket
	python clinical_ETL/CSVConvert.py --input Synthetic_Clinical+Genomic_data/Subset_data --mapping mappings/synthetic2candigv1/manifest.yml
	docker cp Synthetic_Clinical+Genomic_data/Subset_data_map.json $(CANDIG_SERVER):Subset_data_map_candigv1.json
	docker exec $(CANDIG_SERVER) ingest candig-example-data/registry.db $(DATASET2) /Subset_data_map_candigv1.json
	docker restart $(CANDIG_SERVER)

.PHONY: clean
clean: | clean-katsu
	rm -f candig_server.ready
	rm -f katsu.ready
	rm -f hs37d5.fa.gz*
	rm -f reference.ready
	rm -Rf samples
	rm -Rf clinical_ETL.ready
	rm -f opa.ready

.PHONY: clean-katsu
clean-katsu:
	docker cp $(KATSU):Synthetic_Clinical_Data_2_map_mcode.json Synthetic_Clinical+Genomic_data/Synthetic_Clinical_Data_2_map_mcode.json
	python katsu_clean.py $(DATASET) $(DATASET) $(DATASET) $(CHORD_METADATA_INGEST_URL) Synthetic_Clinical+Genomic_data/Synthetic_Clinical_Data_2_map_mcode.json mcodepacket
	rm Synthetic_Clinical+Genomic_data/Synthetic_Clinical_Data_2_map_mcode.json