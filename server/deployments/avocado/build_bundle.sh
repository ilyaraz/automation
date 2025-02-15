#!/bin/sh

set -e

IMAGE_VERSION_CACHE_FILE="last_image_version.txt"

# Read the cached image version if it exists
if [ -f "$IMAGE_VERSION_CACHE_FILE" ]; then
    DEFAULT_DOCKER_IMAGE_VERSION=$(cat "$IMAGE_VERSION_CACHE_FILE")
else
    DEFAULT_DOCKER_IMAGE_VERSION=""
fi

# Obtain DOCKER_IMAGE_VERSION from argument, environment, or prompt
DOCKER_IMAGE_VERSION="${1:-$DOCKER_IMAGE_VERSION}"

if [ -z "$DOCKER_IMAGE_VERSION" ]; then
    if [ -n "$DEFAULT_DOCKER_IMAGE_VERSION" ]; then
        printf "Please enter the image version [%s]: " "$DEFAULT_DOCKER_IMAGE_VERSION"
    else
        printf "Please enter the image version: "
    fi
    read -r INPUT_DOCKER_IMAGE_VERSION
    if [ -z "$INPUT_DOCKER_IMAGE_VERSION" ]; then
        if [ -n "$DEFAULT_DOCKER_IMAGE_VERSION" ]; then
            DOCKER_IMAGE_VERSION="$DEFAULT_DOCKER_IMAGE_VERSION"
            echo "Using cached image version: $DOCKER_IMAGE_VERSION"
        else
            echo "Image version cannot be empty. Exiting."
            exit 1
        fi
    else
        DOCKER_IMAGE_VERSION="$INPUT_DOCKER_IMAGE_VERSION"
    fi
fi

# Save the image version to cache
echo "$DOCKER_IMAGE_VERSION" > "$IMAGE_VERSION_CACHE_FILE"

TS=$(date -u +"%Y%m%d%H%M%S")
sed "s/DOCKER_IMAGE_VERSION/$DOCKER_IMAGE_VERSION/g" docker-compose.yml.template > docker-compose.yml
mkdir -p $TS
cp docker-compose.yml nginx.conf run.sh "$TS"/
cp -r webserver_root "$TS"/
tar -czf bundle_$TS.tar.gz ./$TS
echo "aws s3 cp bundle_$TS.tar.gz s3://json-logger-deployment-bundles/"
echo "aws s3 cp s3://json-logger-deployment-bundles/bundle_$TS.tar.gz ."
