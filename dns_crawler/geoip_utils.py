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

from os import path, getcwd

from sys import stderr

import geoip2.database

from .ip_utils import is_valid_ip_address


def init_geoip(config):
    pwd = getcwd()
    geoip_country = None
    geoip_isp = None
    geoip_asn = None

    if "country" in config["geoip"]:
        try:
            db_path = path.join(pwd, config["geoip"]["country"])
            geoip_country = geoip2.database.Reader(db_path)
        except FileNotFoundError:
            stderr.write(f"GeoIP Country DB cannot be found in '{db_path}'. Disabling.\n")

    if "isp" in config["geoip"]:
        try:
            db_path = path.join(pwd, config["geoip"]["isp"])
            geoip_isp = geoip2.database.Reader(db_path)
        except FileNotFoundError:
            stderr.write(f"GeoIP ISP DB cannot be found in '{db_path}'. Disabling.\n")

    if "asn" in config["geoip"] and not ("isp" in config["geoip"]):
        try:
            db_path = path.join(pwd, config["geoip"]["asn"])
            geoip_asn = geoip2.database.Reader(db_path)
        except FileNotFoundError:
            stderr.write(f"GeoIP ASN DB cannot be found in '{db_path}'. Disabling.\n")

    return (geoip_country, geoip_isp, geoip_asn)


def annotate_geoip(items, dbs, key="value"):
    geoip_country, geoip_isp, geoip_asn = dbs
    if items:
        for item in items:
            ip = item[key]
            if not is_valid_ip_address(ip):
                continue
            try:
                result = {}
                if geoip_country:
                    country = geoip_country.country(ip).country
                    result["country"] = country.iso_code
                if geoip_isp:
                    isp = geoip_isp.isp(ip)
                if geoip_asn and not geoip_isp:
                    isp = geoip_asn.asn(ip)
                if geoip_asn or geoip_isp:
                    result["org"] = isp.autonomous_system_organization
                    result["asn"] = isp.autonomous_system_number
            except Exception as e:
                result["error"] = str(e)
            item["geoip"] = result
    return items
