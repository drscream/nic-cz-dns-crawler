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

from dns_crawler.crawl import process_domain
import json

r = process_domain("nic.cz")

print(json.dumps(r))


def sort_by_value(list):
    return sorted(list, key=lambda k: k["value"])


assert sort_by_value(r["results"]["DNS_LOCAL"]["NS_AUTH"]) == sort_by_value(
    [{"value": "a.ns.nic.cz."}, {"value": "b.ns.nic.cz."}, {"value": "d.ns.nic.cz."}]
)
assert r["results"]["WEB"]["WEB4_80"][0]["status"] == 301
assert r["results"]["WEB"]["WEB4_80"][0]["headers"]["server"] == "nginx"
assert r["results"]["WEB"]["WEB4_443"][0]["tls"]["alpn_protocol"] == "h2"
assert r["results"]["WEB"]["WEB4_443"][0]["tls"]["cert"]["subject"] == "nic.cz"
assert r["results"]["WEB"]["WEB4_443_www"][0]["status"] == 200
assert r["results"]["DNS_LOCAL"]["DNSSEC"]["valid"]
assert r["results"]["DNS_LOCAL"]["DS"][0]["algorithm"] == "ECDSAP256SHA256"
assert r["results"]["DNS_LOCAL"]["WEB4"][0]["geoip"] == {"country": "CZ", "asn": 25192, "org": "CZ.NIC, z.s.p.o."}
