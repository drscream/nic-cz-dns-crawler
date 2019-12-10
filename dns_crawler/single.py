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
from os.path import basename

from .crawl import process_domain
from .timestamp import timestamp


def print_help():
    exe = basename(sys.argv[0])
    sys.stderr.write(
        f"{exe} - a single-threaded crawler to process a small number of domains without a need for Redis\n\n")
    sys.stderr.write(f"Usage: {exe} <file>\n")
    sys.stderr.write(f"       file - plaintext domain list, one domain per line, empty lines are ignored\n")
    sys.exit(1)


def main():
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
            for num, domain in enumerate(domains, start=1):
                print(json.dumps(process_domain(domain)))
                sys.stderr.write(f"{timestamp()} {num}/{domain_count}\n")
            sys.stderr.write(f"{timestamp()} Finished.\n")
    except FileNotFoundError:
        sys.stderr.write(f"File '{filename}' does not exist.\n\n")
        print_help()
    except KeyboardInterrupt:
        sys.exit(0)
