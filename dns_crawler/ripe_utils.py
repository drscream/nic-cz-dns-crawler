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

import requests

from .ip_utils import is_valid_ipv6_address


def ripe_ip_info(ip):
    def get_attr(json, name):
        for field in json:
            if field["name"] == name:
                return field["value"]
        return False

    def get_inetnum(json):
        inetnum = get_attr(json, "inetnum")
        if inetnum is False:
            inetnum = get_attr(json, "inet6num")
        return inetnum

    if is_valid_ipv6_address(ip):
        ripe_url = "https://rest.db.ripe.net/search?type-filter=inet6num"
    else:
        ripe_url = "https://rest.db.ripe.net/search?type-filter=inetnum"
    ripe_url = ripe_url + "&source=ripe&query-string="
    try:
        r = requests.get(ripe_url + ip, headers={"Accept": "application/json"}, timeout=5)
        ripe_json = r.json()["objects"]["object"][0]["attributes"]["attribute"]
    except (KeyError, socket.timeout):
        return None
    return {
        "netname": get_attr(ripe_json, "netname"),
        "inetnum": get_inetnum(ripe_json)
    }


def annotate_ripe(items, key="value"):
    if items:
        for item in items:
            ip = item[key]
            item["ripe"] = ripe_ip_info(ip)
    return items
