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

import logging
import sys
from os.path import basename
from redis import Redis
from rq import Connection, Worker

from .crawl import process_domain, get_json_result  # noqa F401

logger = logging.getLogger("rq.worker")


def print_help():
    exe = basename(sys.argv[0])
    sys.stderr.write(f"{exe} - a single worker process\n\n")
    sys.stderr.write("While it's possible to run it directly, it's meant to be used by dns-crawler-workers.\n")
    sys.stderr.write(f"Usage: {exe} <redis_host> <redis_port> <redis_db> <worker_name>\n")
    sys.exit(1)


class CrawlerWorker(Worker):
    log_result_lifespan = False
    log_job_description = False


def main():
    if "-h" in sys.argv or "--help" in sys.argv or len(sys.argv) != 5:
        print_help()

    redis_host = sys.argv[1]
    redis_port = sys.argv[2]
    redis_db = sys.argv[3]

    with Connection(Redis(host=redis_host, port=redis_port, db=redis_db)):
        q = ["default"]
        w = CrawlerWorker(q, name=sys.argv[4])
        w.work(burst=True)
