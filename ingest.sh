#!/usr/bin/env bash

set -uxo pipefail

DATASET=$1

pip install -r requirements.txt
if [ $? -ne 0 ]; then
  echo "make sure pip is installed" 
  exit 1
fi

# find docker containers:
htsget=$(docker ps --format "{{.Names}}" | grep "htsget")
candig_server=$(docker ps --format "{{.Names}}" | grep "candig-server")


# load variant data
samples=`curl https://raw.githubusercontent.com/CanDIG/mohccn-data/main/Synthetic_Clinical%2BGenomic_data/Synthetic_Clinical_Data_2/ID_Matching_Table.csv`
first=0
Field_Separator=$IFS
IFS=$'\n\r'
for sample in $samples
do
    if [ $first -eq 0 ]; then
        first=1
    else
        val=`echo $sample | awk -F, '{print $3 " " $3 "_0 /samples/" $4 ".vcf.gz"}'`
        com="docker exec $candig_server candig_repo add-variantset candig-example-data/registry.db $DATASET $val -R hs37d5"
        eval $com
        # ingest data into htsget
        val=`echo $sample | awk -F, '{print "python htsget_ingest.py " $4 " /samples/ http://$CANDIG_DOMAIN:$HTSGET_APP_PORT $DATASET"}'`
        eval $val

    fi
done

docker restart $candig_server
IFS=Field_Separator

