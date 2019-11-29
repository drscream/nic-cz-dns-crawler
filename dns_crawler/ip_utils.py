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

import ipaddress


def is_valid_ipv6_address(ip):
    try:
        ipaddress.IPv6Address(ip)
    except ValueError:
        return False
    return True


def is_valid_ipv4_address(ip):
    try:
        ipaddress.IPv4Address(ip)
    except ValueError:
        return False
    return True


def is_valid_ip_address(ip):
    return is_valid_ipv4_address(ip) or is_valid_ipv6_address(ip)
