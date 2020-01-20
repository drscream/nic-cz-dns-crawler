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


import socket

from .dns_utils import get_record


def parse_helo(h):
    return h[1].decode("utf-8").split("\n")


def get_mailserver_info(host, timeout, resolver):
    result = {}
    result["host"] = host
    result["TLSA"] = get_record("_25._tcp." + host, "TLSA", resolver)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, 25))
    except (OSError, socket.timeout, ConnectionRefusedError) as e:
        result["error"] = str(e)
    else:
        try:
            result["banner"] = s.recv(1024).decode()
        except Exception as e:
            result["error"] = str(e)
        s.close()
    return result


def get_mx_info(mx_records, timeout, resolver):
    results = []
    if not mx_records:
        return None
    for mx in mx_records:
        if mx and mx["value"]:
            host = mx["value"].split(" ")[-1]
            if host and host != ".":
                results.append(get_mailserver_info(host, timeout, resolver))
    return results
