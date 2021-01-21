#!/bin/bash

img="helb/dns-crawler"
tag=$(git describe --abbrev=0 --tags)

docker build -t "$img:$tag" . --no-cache
docker push "$img:$tag"