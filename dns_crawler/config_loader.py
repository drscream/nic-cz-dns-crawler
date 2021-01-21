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

import pickle
import sys
from os import getcwd, path
from shutil import copy2

import yaml

from .ip_utils import is_valid_ip_address
from .timestamp import timestamp

default_config_filename = "config.yml"

defaults = {
    "geoip": {
        "country": "/usr/share/GeoIP/GeoLite2-Country.mmdb",
        "asn": "/usr/share/GeoIP/GeoLite2-ASN.mmdb"
    },
    "dns": {
        "resolvers": [
            "193.17.47.1",
            "2001:148f:ffff::1"
        ],
        "additional": [],
        "auth_chaos_txt": [
            "version.bind",
            "hostname.bind"
        ],
        "check_www": True
    },
    "timeouts": {
        "job": 80,
        "dns": 2,
        "http": 2,
        "http_read": 5,
        "mail": 2,
        "cache": 3600
    },
    "mail": {
        "get_banners": False,
        "ports": [25, 465, 587]
    },
    "web": {
        "save_content": False,
        "save_binary": True,
        "max_redirects": 6,
        "save_cert_chain": False,
        "user_agent": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36",
        "accept_language": "en-US;q=0.9,en;q=0.8",
        "content_size_limit": 5120000,
        "max_ips_per_domain": None,
        "check_http": True,
        "check_https": True,
        "check_ipv4": True,
        "check_ipv6": True,
        "save_intermediate_steps": True
    },
    "connectivity_check_ips": {
        "ipv4": "193.17.47.1",
        "ipv6": "2001:148f:ffff::1"
    },
    "save_worker_hostname": False
}


def merge_dicts(source, destination):
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            merge_dicts(value, node)
        else:
            if isinstance(value, str):
                if is_valid_ip_address(value):
                    destination[key] = value
                elif value[0].isdigit():
                    destination[key] = float(value)
                elif value == "False":
                    destination[key] = False
                elif value == "True":
                    destination[key] = True
                else:
                    destination[key] = value
            else:
                destination[key] = value
    return destination


def load_config_from_file(filename=default_config_filename):
    pwd = getcwd()
    try:
        with open(path.join(pwd, filename), "r", encoding="utf-8") as conf_file:
            config_from_file = yaml.safe_load(conf_file)
            if not config_from_file:
                sys.stderr.write(f"{timestamp()} Didn't find anything in the config file. Using defaults.\n")
                config = defaults
            elif "http_timeout" in config_from_file or \
                 "dns_timeout" in config_from_file or \
                 "save_web_content" in config_from_file:
                sys.stderr.write(f"{timestamp()} Incompatible config file loaded (the format" +
                                 " changed with v1.2, see README). Using defaults instead.\n")
                config = defaults
            elif "resolvers" in config_from_file:
                sys.stderr.write(f"{timestamp()} Incompatible config file loaded (the format" +
                                 " changed with v1.4, see README). Automatically converting to" +
                                 " the new format.\n")
                with_resolvers = merge_dicts(config_from_file, {
                    "dns": {
                        "resolvers": config_from_file["resolvers"]
                    }
                })
                config = merge_dicts(with_resolvers, defaults)
                del config["resolvers"]
                copy2(path.join(pwd, filename), path.join(pwd, f"{filename}.bak"))
                with open(path.join(pwd, filename), "w", encoding="utf-8") as file_w:
                    yaml.safe_dump(config, file_w, default_flow_style=False)
            else:
                config = merge_dicts(config_from_file, defaults)
    except FileNotFoundError:
        config = defaults
    return config


def load_config(filename=default_config_filename, redis=None, hostname=None, save=False):
    if redis is not None:
        key_controller = "crawler-config"
        if hostname:
            key = f"{key_controller}-{hostname}"
            cached = redis.get(key)
            if cached is not None:
                return pickle.loads(cached)
            else:
                try:
                    config_controller = pickle.loads(redis.get(key_controller))
                except TypeError:
                    from .controller import ControllerNotRunning
                    raise ControllerNotRunning()
                config_workers = load_config_from_file(filename)
                config = merge_dicts(config_controller, config_workers)
                if save:
                    redis.set(key, pickle.dumps(config))
                return config
        else:
            key = key_controller
            cached = redis.get(key)
            if cached is not None:
                return pickle.loads(cached)
            else:
                config = load_config_from_file(filename)
                if save:
                    redis.set(key, pickle.dumps(config))
                return config
    else:
        return load_config_from_file(filename)
