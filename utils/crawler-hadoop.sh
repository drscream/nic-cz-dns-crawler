#!/bin/bash
# Pushes the results file to Hadoop and notifies a Mattermost channel.
# usage: hadoop-crawler.sh YYYYMMDD
set -e;
mmchannel="crawler"
mmhook="https://mattermost.foo.bar/hooks/xxxxxxxxxxxx"
year=$(date -d "$1" "+%Y")
month=$(date -d "$1" "+%-m")
month_zero=$(date -d "$1" "+%m")
day=$(date -d "$1" "+%-d")
day_zero=$(date -d "$1" "+%d")
date="$year$month_zero$day_zero"
hadoop_dir="/dns-crawler/year=$year/month=$month/day=$day"
hadoop_file="results.json"
local_file="$HOME/results/$date.json"
size=$(du -m "$local_file" | cut -f1 | sed "s/$/ MB/")
echo "Date: $date"
echo "Size: $size"
ssh hadoop-node.host "HADOOP_USER_NAME=hdfs hadoop fs -mkdir -p $hadoop_dir;"
cat "$local_file" | ssh hadoop-node.host "HADOOP_USER_NAME=hdfs hadoop fs -put - $hadoop_dir/$hadoop_file;"
curl -X POST -H 'Content-Type: application/json' -d "{\"text\": \":robot: fresh crawler results uploaded to \`$hadoop_dir/$hadoop_file\` ($size)\", \"channel\": \"$mmchannel\", \"username\": \"dns-crawler\"}" "$mmhook"
echo "pushed to hadoop"

