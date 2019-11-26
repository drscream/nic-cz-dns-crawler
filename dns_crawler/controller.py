import json
import sys
import threading
from multiprocessing import cpu_count
from time import sleep

import rq
from redis import Redis
from rq import Queue, job
from rq.registry import FinishedJobRegistry

from .config_loader import load_config
from .crawl import process_domain
from .timestamp import timestamp


def print_help():
    sys.stderr.write(f"Usage: {sys.argv[0]} <file>\n")
    sys.stderr.write(f"       file - plaintext domain list, one domain per line (separated by \\n)\n")
    sys.exit(1)


def create_jobs(domains, function, queue, timeout, should_stop):
    for domain in domains:
        if should_stop():
            break
        create_job(domain, function, queue, timeout)


def create_job(domain, function, queue, timeout):
    queue.enqueue(function, domain, job_id=domain, result_ttl=-1, job_timeout=timeout)


def main():
    POLL_INTERVAL = 5
    cpus = cpu_count()
    config = load_config("config.yml")
    redis = Redis()
    queue = Queue(connection=redis)
    finished_registry = FinishedJobRegistry(connection=redis)
    stop_threads = False

    try:
        filename = sys.argv[1]
    except IndexError:
        print_help()

    try:
        with open(filename, "r") as file:
            sys.stderr.write(f"{timestamp()} Reading domains from {filename}.\n")
            domains = file.read().splitlines()
            domain_count = len(domains)
            finished_count = 0
            created_count = 0
            parts = cpus * 8
            domains_per_part = int(domain_count / parts)
            sys.stderr.write(f"{timestamp()} Creating job queue using {parts} threads.\n")
            redis.set("locked", 1)

            for thread_num in range(parts):
                if thread_num == parts - 1:  # last one
                    end = domain_count
                else:
                    end = (thread_num + 1) * domains_per_part
                part = domains[(thread_num * domains_per_part):end]
                t = threading.Thread(target=create_jobs,
                                     args=(part, process_domain, queue, config["job_timeout"], lambda: stop_threads))
                t.start()

            while created_count < domain_count:
                sys.stderr.write(f"{timestamp()} {created_count}/{domain_count} jobs created.\n")
                created_count = queue.count
                sleep(POLL_INTERVAL)

            sys.stderr.write(f"{timestamp()} Created {domain_count} jobs. Unlocking queue and waiting for workers…\n")
            redis.set("locked", 0)

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
        created_count = queue.count
        sys.stderr.write(f"{timestamp()} Cancelled. Deleting {created_count} jobs…\n")
        stop_threads = True
        redis.delete("locked")
        queue.delete(delete_jobs=True)
        while 0 < created_count:
            sleep(POLL_INTERVAL)
            created_count = queue.count
            sys.stderr.write(f"{timestamp()} {created_count} jobs remaining.\n")
        sys.stderr.write(f"{timestamp()} All jobs deleted, exiting.\n")
        sys.exit(1)

    except FileNotFoundError:
        sys.stderr.write(f"File '{filename}' does not exist.\n\n")
        print_help()
