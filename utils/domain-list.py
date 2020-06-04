import csv
from datetime import datetime, timedelta
from sys import argv, stderr, exit

if len(argv) < 2:
    stderr.write(f"Usage: {argv[0]} [file] [max age in days]\n")
    exit(1)

if len(argv) < 3:
    for row in csv.DictReader(open(argv[1])):
        if row["domainname"].endswith("cz"):
            print(row["domainname"])
else:
    now = datetime.now()
    start = datetime.now() - timedelta(days=int(argv[2]))
    for row in csv.DictReader(open(argv[1])):
        regdate = datetime.strptime(row["current_registration_date"], "%Y-%m-%dT%H:%M:%SZ")
        if row["domainname"].endswith("cz") and regdate >= start:
            print(row["domainname"])
