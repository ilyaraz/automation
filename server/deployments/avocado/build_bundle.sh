#!/bin/sh

set -xe

TS=$(date -u +"%Y%m%d%H%M%S")
mkdir -p $TS
cp docker-compose-bootstrap.yml docker-compose-main.yml nginx_bootstrap.conf nginx_main.conf run.sh "$TS"/
cp -r webserver_root "$TS"/
tar -czf bundle_$TS.tar.gz ./$TS
echo "aws s3 cp bundle_$TS.tar.gz s3://json-logger-deployment-bundles/"
echo "aws s3 cp s3://json-logger-deployment-bundles/bundle_$TS.tar.gz ."
