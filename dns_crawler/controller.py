# Copyright © 2019 CZ.NIC, z. s. p. o.
#
# This file is part of dns-crawler.
#
# dns-crawler is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This software is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License. If not,
# see <http://www.gnu.org/licenses/>.

import json
import sys
import threading
from multiprocessing import cpu_count
from os.path import basename
from time import sleep

import rq
from redis import Redis
from rq import Queue, job
from rq.registry import FinishedJobRegistry

from .config_loader import load_config
from .crawl import process_domain
from .redis_utils import get_redis_host
from .timestamp import timestamp

POLL_INTERVAL = 5


def print_help():
    exe = basename(sys.argv[0])
    sys.stderr.write(f"{exe} - the main process controlling the job queue and printing results.\n\n")
    sys.stderr.write(f"Usage: {exe} <file> [redis]\n")
    sys.stderr.write(f"       file - plaintext domain list, one domain per line, empty lines are ignored\n")
    sys.stderr.write(f"       redis - redis host:port:db, localhost:6379:0 by default\n\n")
    sys.stderr.write(f"Examples: {exe} domains.txt\n")
    sys.stderr.write(f"          {exe} domains.txt 192.168.0.22:4444:0\n")
    sys.stderr.write(f"          {exe} domains.txt redis.foo.bar:7777:2\n")
    sys.stderr.write(f"          {exe} domains.txt redis.foo.bar # port 6379 and DB 0 will be used if not specified\n")
    sys.exit(1)


def create_jobs(domains, function, queue, timeout, should_stop):
    for domain in domains:
        if should_stop():
            break
        create_job(domain, function, queue, timeout)


def create_job(domain, function, queue, timeout):
    queue.enqueue(function, domain, job_id=domain, result_ttl=-1, job_timeout=timeout)


def main():
    if "-h" in sys.argv or "--help" in sys.argv or len(sys.argv) < 2:
        print_help()

    cpus = cpu_count()
    config = load_config("config.yml")

    try:
        redis_host = get_redis_host(sys.argv, 2)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        exit(1)
    redis = Redis(host=redis_host[0], port=redis_host[1], db=redis_host[2])

    redis.flushdb()
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
            domains = [line for line in file.read().splitlines() if line.strip()]
            domain_count = len(domains)
            sys.stderr.write(f"{timestamp()} Read {domain_count} domain{('s' if domain_count > 1 else '')}.\n")
            finished_count = 0
            created_count = 0
            parts = cpus * 4
            if parts * 1000 > domain_count:
                parts = 1
            domains_per_part = int(domain_count / parts)
            sys.stderr.write(f"{timestamp()} Creating job queue using {parts} thread{('s' if parts > 1 else '')}.\n")
            redis.set("locked", 1)

            if parts == 1:
                create_jobs(domains, process_domain, queue, config["job_timeout"], lambda: False)
            else:
                for thread_num in range(parts):
                    if thread_num == parts - 1:  # last one
                        end = domain_count
                    else:
                        end = (thread_num + 1) * domains_per_part
                    part = domains[(thread_num * domains_per_part):end]
                    t = threading.Thread(target=create_jobs,
                                         args=(part, process_domain, queue,
                                               config["job_timeout"], lambda: stop_threads))
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
                finished_jobs = job.Job.fetch_many(finished_domains, connection=redis)
                for finished_job in finished_jobs:
                    if not finished_job:
                        continue
                    result = finished_job.result
                    json.dump(result, sys.stdout, ensure_ascii=False, check_circular=False, separators=(",", ":"))
                    sys.stdout.write("\n")
                    finished_job.delete()
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
