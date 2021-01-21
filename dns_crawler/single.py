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

import sys
from os.path import basename

from .crawl import get_json_result
from .timestamp import timestamp


def print_help():
    exe = basename(sys.argv[0])
    sys.stderr.write(
        f"{exe} - a single-threaded crawler to process a small number of domains without a need for Redis\n\n")
    sys.stderr.write(f"Usage: {exe} <file>\n")
    sys.stderr.write("       file - plaintext domain list, one domain per line, empty lines are ignored\n")
    sys.exit(1)


def main():
    if "-h" in sys.argv or "--help" in sys.argv or len(sys.argv) < 2:
        print_help()

    filename = sys.argv[1]

    try:
        try:
            file = open(filename, "r", encoding="utf-8")
        except FileNotFoundError:
            sys.stderr.write(f"File '{filename}' does not exist.\n\n")
            print_help()
        sys.stderr.write(f"{timestamp()} Reading domains from {filename}.\n")
        domains = [line for line in file.read().splitlines() if line.strip()]
        domain_count = len(domains)
        sys.stderr.write(f"{timestamp()} Read {domain_count} domain{('s' if domain_count > 1 else '')}.\n")
        for num, domain in enumerate(domains, start=1):
            print(get_json_result(domain), flush=True)
            sys.stderr.write(f"{timestamp()} {num}/{domain_count}\n")
        sys.stderr.write(f"{timestamp()} Finished.\n")
    except KeyboardInterrupt:
        sys.exit(0)
