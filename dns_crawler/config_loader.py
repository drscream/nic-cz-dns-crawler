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

import pickle
import sys
from os import getcwd, path

import yaml

from .controller import ControllerNotRunning
from .timestamp import timestamp

default_config_filename = "config.yml"

defaults = {
    "geoip": {
        "country": "/usr/share/GeoIP/GeoLite2-Country.mmdb",
        "asn": "/usr/share/GeoIP/GeoLite2-ASN.mmdb"
    },
    "dns": {
        "resolvers": [
            "193.17.47.1"
        ],
        "additional": []
    },
    "timeouts": {
        "job": 80,
        "dns": 2,
        "http": 2,
        "http_read": 5,
        "mail": 2,
        "cache": 900
    },
    "mail": {
        "get_banners": False
    },
    "web": {
        "save_content": False,
        "strip_html": False,
        "max_redirects": 6,
        "save_cert_chain": False,
        "user_agent": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36",
        "accept_language": "en-US;q=0.9,en;q=0.8"
    }
}


def merge_dicts(source, destination):
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            merge_dicts(value, node)
        else:
            if isinstance(value, str):
                if value.isdigit():
                    destination[key] = int(value)
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
        with open(path.join(pwd, filename), "r") as conf_file:
            config_from_file = yaml.safe_load(conf_file)
            if "http_timeout" in config_from_file or \
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
                noalias_dumper = yaml.dumper.SafeDumper
                noalias_dumper.ignore_aliases = lambda self, data: True
                with open(path.join(pwd, filename), "w") as file_w:
                    yaml.safe_dump(config, file_w, default_flow_style=False, Dumper=noalias_dumper)
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
