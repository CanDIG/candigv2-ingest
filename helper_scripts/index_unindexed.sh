#!/usr/bin/env bash

set -Euo pipefail

postgres=$(docker ps --format "{{.Names}}" | grep postgres-db | awk '{print $1}')

length=$(docker exec $postgres sh -c "psql -U admin -d drs -c \"copy (select id from drs_object where description = 'sequence_variation' and meta_data ? 'index_status') To '/tmp/unindexed.csv';\"" | awk '{print $NF}')

if [ $length -gt 0 ]; then
    myfile=$(mktemp --suffix ".csv")
    copy=$(docker cp $postgres:/tmp/unindexed.csv $myfile)
    remove=$(docker exec $postgres rm /tmp/unindexed.csv)
    echo "# $length variant files to index"
    echo "# Set the env vars \$TOKEN and \$CANDIG_URL before running the following curl commands."
    for id in $(cat $myfile)
    do
        echo curl "\"\$CANDIG_URL/genomics/htsget/v1/$id/index?force=true\" -H \"Content-Type: application/json\" -H \"Authorization: Bearer \$TOKEN\""
    done
    rm $myfile
else
    echo "# No unindexed entries were found"
fi
