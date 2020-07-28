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

import ipaddress
import pickle
import socket


def is_valid_ipv6_address(ip):
    try:
        addr = ipaddress.IPv6Address(ip)
    except ValueError:
        return False
    return addr.is_global


def is_valid_ipv4_address(ip):
    try:
        addr = ipaddress.IPv4Address(ip)
    except ValueError:
        return False
    return addr.is_global


def is_valid_ip_address(ip):
    return is_valid_ipv4_address(ip) or is_valid_ipv6_address(ip)


def get_source_address(v, ip):
    if ip is None:
        return None
    if v == 6:
        inet = socket.AF_INET6
    elif v == 4:
        inet = socket.AF_INET
    target = (ip, 53)
    try:
        sock = socket.socket(inet, socket.SOCK_DGRAM)
        sock.connect(target)
        source_ip = sock.getsockname()[0]
        sock.close()
    except OSError:
        return None
    return source_ip


def get_source_addresses(config, redis=None, hostname=socket.gethostname()):
    if redis is not None:
        key = f"sourceips-{hostname}"
        cached = redis.get(key)
        if cached is not None:
            return pickle.loads(cached)
        else:
            ips = (get_source_address(4, config["connectivity_check_ips"]["ipv4"]),
                   get_source_address(6, config["connectivity_check_ips"]["ipv6"]))
            redis.set(key, pickle.dumps(ips))
            return ips
    else:
        return (get_source_address(4, config["connectivity_check_ips"]["ipv4"]),
                get_source_address(6, config["connectivity_check_ips"]["ipv6"]))
