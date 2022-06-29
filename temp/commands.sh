source env.sh
python opa_ingest.py --dataset mcode-synthetic --user temp/users.txt > temp/access.json
docker cp temp/access.json candigv2_opa_1:/app/permissions_engine/access.json
cat ../CanDIGv2/tmp/ssl/cert.pem >> ../CanDIGv2/bin/miniconda3/envs/candig/lib/python3.7/site-packages/certifi/cacert.pem
cd temp/samples/
python ../../s3_ingest.py --samplefile ../samples.txt --dataset mcode-synthetic --endpoint candig-federation-1.hpc4healthlocal:9000 --bucket samples --awsfile ../s3.txt
cd ../..
python htsget_ingest.py --samplefile temp/samples.gz.txt --dataset mcode-synthetic --endpoint candig-federation-1.hpc4healthlocal:9000 --bucket samples --awsfile temp/s3.txt
bash temp/candigv1_copy.sh
docker cp temp/clinical_map.json candigv2_chord-metadata_1:/clinical_map.json
