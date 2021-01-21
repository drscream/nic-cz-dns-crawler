# Copyright © 2019-2020 CZ.NIC, z. s. p. o.
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of dns-crawler.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import pickle
import sys
from os.path import basename
from time import sleep
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from rq import Queue
from rq.job import Job
from rq.registry import FinishedJobRegistry

from .config_loader import default_config_filename, load_config
from .crawl import get_json_result
from .redis_utils import get_redis_host
from .timestamp import timestamp

POLL_INTERVAL = 5
INPUT_CHUNK_SIZE = 10000


class ControllerNotRunning(Exception):
    pass


def print_help():
    exe = basename(sys.argv[0])
    sys.stderr.write(f"{exe} - the main process controlling the job queue and printing results.\n\n")
    sys.stderr.write(f"Usage: {exe} <file> [redis]\n")
    sys.stderr.write("       file - plaintext domain list, one domain per line, empty lines are ignored\n")
    sys.stderr.write("       redis - redis host:port:db, localhost:6379:0 by default\n\n")
    sys.stderr.write(f"Examples: {exe} domains.txt\n")
    sys.stderr.write(f"          {exe} domains.txt 192.168.0.22:4444:0\n")
    sys.stderr.write(f"          {exe} domains.txt redis.foo.bar:7777:2\n")
    sys.stderr.write(f"          {exe} domains.txt redis.foo.bar # port 6379 and DB 0 will be used if not specified\n")
    sys.exit(1)


def create_jobs(domains, function, redis, queue, timeout):
    job_count = 0
    pipe = redis.pipeline()
    for domain in domains:
        job = Job.create(function, args=(domain,), id=domain, timeout=timeout,
                         result_ttl=-1, connection=redis, description=domain)
        queue.enqueue_job(job, pipeline=pipe)
        job_count += 1
    pipe.execute()
    return job_count


def main():
    if "-h" in sys.argv or "--help" in sys.argv or len(sys.argv) < 2:
        print_help()

    try:
        redis_host = get_redis_host(sys.argv, 2)
    except Exception as e:
        sys.stderr.write(f"{timestamp()} {str(e)}\n")
        sys.exit(1)
    redis = Redis(host=redis_host[0], port=redis_host[1], db=redis_host[2])

    redis.flushdb()
    config = load_config(default_config_filename, redis, save=True)
    finished_registry = FinishedJobRegistry(connection=redis)

    try:
        filename = sys.argv[1]
    except IndexError:
        print_help()

    try:
        sys.stderr.write(f"{timestamp()} Reading domains from {filename}.\n")
        input_file = open(filename, "r", encoding="utf-8")
        sys.stderr.write(
            f"{timestamp()} Creating job queue…\n")
        redis.set("locked", 1)
        queue = Queue(connection=redis)
        domain_count = 0
        read_domains = []
        for line in input_file:
            read_domains.append(line.rstrip())
            if len(read_domains) == INPUT_CHUNK_SIZE:
                domain_count = domain_count + create_jobs(read_domains, get_json_result, queue=queue,
                                                          redis=redis, timeout=config["timeouts"]["job"])
                sys.stderr.write(f"{timestamp()} {domain_count}\n")
                read_domains = []
        domain_count = domain_count + create_jobs(read_domains, get_json_result, queue=queue,
                                                  redis=redis, timeout=config["timeouts"]["job"])
        sys.stderr.write(f"{timestamp()} {domain_count}\n")
        input_file.close()

        finished_count = 0
        sys.stderr.write(f"{timestamp()} Created {domain_count} jobs. Unlocking queue and waiting for workers…\n")

        redis.set("locked", 0)

        while finished_count < domain_count:
            finished_domains = finished_registry.get_job_ids()
            if len(finished_domains) > 0:
                pipe = redis.pipeline()
                hashes = []
                for domain in finished_domains:
                    hash = f"rq:job:{domain}"
                    hashes.append(hash)
                    pipe.hget(hash, "result")
                results = pipe.execute()
                pipe = redis.pipeline()
                count = 0
                for index, result in enumerate(results):
                    if result:
                        count = count + 1
                        try:
                            print(pickle.loads(result))
                        except pickle.UnpicklingError:
                            sys.stderr.write(f"{timestamp()} UnpicklingError: {hashes[index]}\n")
                            continue
                        else:
                            pipe.delete(hashes[index])
                pipe.execute()
                finished_count = finished_count + count
            sys.stderr.write(f"{timestamp()} {finished_count}/{domain_count}\n")
            sleep(POLL_INTERVAL)
        queue.delete(delete_jobs=True)
        sys.exit(0)

    except KeyboardInterrupt:
        created_count = queue.count
        sys.stderr.write(f"{timestamp()} Cancelled. Deleting {created_count} jobs…\n")
        redis.flushdb()
        sys.stderr.write(f"{timestamp()} All jobs deleted, exiting.\n")
        sys.exit(1)

    except RedisConnectionError:
        sys.stderr.write(f"{timestamp()} Connection to Redis lost. :(\n")
        sys.exit(1)

    except FileNotFoundError:
        sys.stderr.write(f"File '{filename}' does not exist.\n\n")
        print_help()
