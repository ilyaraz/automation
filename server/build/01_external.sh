#!/bin/sh

set -xe

cp ../requirements.txt .
cp -r ../src .
TS=$(date -u +"%Y%m%d%H%M%S")
docker build . -t ilyaraz/json_logger:$TS -f Dockerfile --platform linux/amd64
echo docker push ilyaraz/json_logger:$TS > 02_external.sh
chmod +x 02_external.sh
