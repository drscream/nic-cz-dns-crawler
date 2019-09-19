import json
import csv
import sys

writer = csv.writer(sys.stdout)

writer.writerow([
    "domain",
    "timestamp",
    "dnslocal_dnsauth",
    ])

for line in sys.stdin:
    data = json.loads(line)
    writer.writerow([
        data["domain"],
        data["timestamp"],
        data["results"]["DNS_LOCAL"]["DNS_AUTH"]
    ])
