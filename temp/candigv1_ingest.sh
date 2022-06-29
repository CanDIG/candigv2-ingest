#!/usr/bin/env bash

set -xuo pipefail

# Execute this script with the path to the candig database as an argument.

DATABASE=$1

ingest
if [ $? -ne 1 ]; then
  echo "Is candig-ingest installed? https://candig-server.readthedocs.io/en/v1.5.0-alpha/datarepo.html#ingest"
  exit 1
fi

ingest $DATABASE mcode-synthetic candigv1_data.json

candig_repo add-variantset $DATABASE mcode-synthetic UBU001 UBU001 /data/vcfs/HG00096.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU003 UBU003 /data/vcfs/HG00097.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU005 UBU005 /data/vcfs/HG00099.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU009 UBU009 /data/vcfs/HG00100.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU024 UBU024 /data/vcfs/HG00101.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU010 UBU010 /data/vcfs/HG00102.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU025 UBU025 /data/vcfs/HG00103.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU012 UBU012 /data/vcfs/HG00104.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU022 UBU022 /data/vcfs/HG00106.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU032 UBU032 /data/vcfs/HG00108.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU033 UBU033 /data/vcfs/HG00109.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU026 UBU026 /data/vcfs/HG00110.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU028 UBU028 /data/vcfs/HG00111.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU035 UBU035 /data/vcfs/HG00112.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU036 UBU036 /data/vcfs/HG00113.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU040 UBU040 /data/vcfs/HG00114.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU046 UBU046 /data/vcfs/HG00116.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU047 UBU047 /data/vcfs/HG00117.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU048 UBU048 /data/vcfs/HG00118.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU049 UBU049 /data/vcfs/HG00119.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU013 UBU013 /data/vcfs/HG00121.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU034 UBU034 /data/vcfs/HG00122.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU015 UBU015 /data/vcfs/HG00123.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU016 UBU016 /data/vcfs/HG00124.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU017 UBU017 /data/vcfs/HG00125.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU050 UBU050 /data/vcfs/HG00126.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU042 UBU042 /data/vcfs/HG00127.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU019 UBU019 /data/vcfs/HG00128.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU051 UBU051 /data/vcfs/HG00129.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU020 UBU020 /data/vcfs/HG00130.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU052 UBU052 /data/vcfs/HG00131.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU023 UBU023 /data/vcfs/HG00134.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU053 UBU053 /data/vcfs/HG00138.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU054 UBU054 /data/vcfs/HG00139.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU055 UBU055 /data/vcfs/HG00140.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU056 UBU056 /data/vcfs/HG00141.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU057 UBU057 /data/vcfs/HG00142.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU058 UBU058 /data/vcfs/HG00143.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU059 UBU059 /data/vcfs/HG00150.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU002 UBU002 /data/vcfs/HG00151.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU027 UBU027 /data/vcfs/HG00155.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU030 UBU030 /data/vcfs/HG00159.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU043 UBU043 /data/vcfs/HG00160.vcf.gz -R hs37d5
candig_repo add-variantset $DATABASE mcode-synthetic UBU021 UBU021 /data/vcfs/HG00234.vcf.gz -R hs37d5
