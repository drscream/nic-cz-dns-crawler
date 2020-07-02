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
from .ip_utils import is_valid_ipv4_address, is_valid_ipv6_address


def get_smtp_banner(host_ip, port, timeout):
    result = {"port": port}
    if is_valid_ipv4_address(host_ip):
        inet = socket.AF_INET
    elif is_valid_ipv6_address(host_ip):
        inet = socket.AF_INET6
    else:
        return None
    try:
        s = socket.socket(inet, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host_ip, port))
    except (OSError, socket.timeout, ConnectionRefusedError) as e:
        result["error"] = str(e)
    else:
        try:
            banner = s.recv(1024).decode().replace("\r\n", "")
            result["banner"] = banner
        except Exception as e:
            result["error"] = str(e)
        s.close()
        return result


def get_mailserver_info(host, ports, timeout, get_banners, cache_timeout, resolver, redis):
    cache_key_host = f"cache-mail-host-{host}"
    if redis is not None:
        cached_host = redis.get(cache_key_host)
        if cached_host is not None:
            redis.expire(cache_key_host, cache_timeout)
            return json.loads(cached_host.decode("utf-8"))
    result = {}
    result["host"] = host
    result["TLSA"] = {}
    for port in ports:
        result["TLSA"][port] = parse_tlsa(get_record(f"_{port}._tcp." + host, "TLSA", resolver))
    if get_banners:
        result["banners"] = []
        host_ip4s = get_record(host, "A", resolver)
        host_ip6s = get_record(host, "AAAA", resolver)
        host_ips = host_ip4s or [] + host_ip6s or []
        for host_ip in host_ips:
            host_ip = host_ip["value"]
            cache_key_ip = f"cache-mail-ip-{host_ip}"
            if redis is not None:
                cached_ip = redis.get(cache_key_ip)
                if cached_ip is not None:
                    redis.expire(cache_key_ip, cache_timeout)
                    result["banners"].append(json.loads(cached_ip.decode("utf-8")))
                    continue
            ip_banners = {"ip": host_ip, "banners": []}
            for port in ports:
                ip_banners["banners"].append(get_smtp_banner(host_ip, port, timeout))
            if redis is not None:
                redis.set(cache_key_ip, json.dumps(ip_banners), ex=cache_timeout)
            result["banners"].append(ip_banners)
    if redis is not None:
        redis.set(cache_key_host, json.dumps(result), ex=cache_timeout)
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
