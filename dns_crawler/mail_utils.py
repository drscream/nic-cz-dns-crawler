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


import json
import socket

from .dns_utils import get_record, parse_tlsa


def get_mailserver_info(host, ports, timeout, get_banners, cache_timeout, resolver, redis):
    cache_key = f"cache-mail-{host}"
    if redis is not None:
        cached = redis.get(cache_key)
        if cached is not None:
            redis.expire(cache_key, cache_timeout)
            return json.loads(cached.decode("utf-8"))
    result = {}
    result["host"] = host
    result["TLSA"] = {}
    if get_banners:
        result["banners"] = {}
        result["errors"] = {}
    for port in ports:
        result["TLSA"][port] = parse_tlsa(get_record(f"_{port}._tcp." + host, "TLSA", resolver))
        if get_banners:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                s.connect((host, 25))
            except (OSError, socket.timeout, ConnectionRefusedError) as e:
                result["errors"][port] = str(e)
            else:
                try:
                    result["banners"][port] = s.recv(1024).decode().replace("\r\n", "")
                except Exception as e:
                    result["errors"][port] = str(e)
                s.close()
    if redis is not None:
        redis.set(cache_key, json.dumps(result), ex=cache_timeout)
    return result


def get_mx_info(mx_records, ports, timeout, get_banners, cache_timeout, resolver, redis):
    results = []
    if not mx_records:
        return None
    for mx in mx_records:
        if mx and mx["value"]:
            host = mx["value"].split(" ")[-1]
            if host and host != ".":
                results.append(get_mailserver_info(host, ports, timeout, get_banners, cache_timeout, resolver, redis))
    return results
