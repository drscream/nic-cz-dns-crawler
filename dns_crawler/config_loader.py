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

from os import path, getcwd

import yaml

defaults = {
    "geoip": {
        "country": "/usr/share/GeoIP/GeoIP2-Country.mmdb",
        "isp": "/usr/share/GeoIP/GeoIP2-ISP.mmdb"},
    "dns": [
        "193.17.47.1"
    ],
    "job_timeout": "80",
    "dns_timeout": "2",
    "http_timeout": "2",
    "save_web_content": "False",
    "strip_html": "True"
}


def load_config(filename):
    pwd = getcwd()
    try:
        with open(path.join(pwd, filename), "r") as conf_file:
            config_from_file = yaml.load(conf_file, Loader=yaml.BaseLoader)
            config = {**defaults, **config_from_file}
    except FileNotFoundError:
        config = defaults
    return config
