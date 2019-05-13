from redis import Redis
import rq
from rq import Queue, job
from rq.registry import FinishedJobRegistry
import sys
from crawl import process_domain
from time import sleep
import json
from datetime import datetime

POLL_INTERVAL = 2


def print_help():
    sys.stderr.write(f"Usage: {sys.argv[0]} <file>\n")
    sys.stderr.write(f"       file - plaintext domain list, one domain per line (separated by \\n)\n")
    sys.exit(1)


def timestamp():
    return f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"


try:
    filename = sys.argv[1]
except IndexError:
    print_help()

redis = Redis()
queue = Queue(connection=redis)
finished_registry = FinishedJobRegistry(connection=redis)

try:
    with open(filename, "r") as file:
        domain_count = 0
        finished_count = 0
        for line in file:
            domain_count = domain_count + 1
            domain = line.strip()
            queue.enqueue(process_domain, domain, job_id=domain)
        sys.stderr.write(f"{timestamp()} Created {domain_count} jobs.\n")
        while finished_count < domain_count:
            finished_domains = finished_registry.get_job_ids()
            finished_count = finished_count + len(finished_domains)
            sys.stderr.write(f"{timestamp()} {finished_count}/{domain_count}\n")
            for domain in finished_domains:
                try:
                    finished_job = job.Job.fetch(domain, connection=redis)
                    result = finished_job.result
                    print(json.dumps(result))
                    finished_job.delete()
                except rq.exceptions.NoSuchJobError:
                    pass
            sleep(POLL_INTERVAL)
        queue.delete(delete_jobs=True)
        sys.exit(0)

except KeyboardInterrupt:
    queue.delete(delete_jobs=True)
    sys.stderr.write(f"\r{timestamp()} Cancelled")
    sys.exit(1)
except FileNotFoundError:
    sys.stderr.write(f"File '{filename}' does not exist.\n\n")
    print_help()
