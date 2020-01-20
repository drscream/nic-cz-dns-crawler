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

import json
import re
from copy import deepcopy
from datetime import datetime

from .config_loader import load_config
from .dns_utils import (annotate_dns_algorithm, check_dnssec,
                        get_local_resolver, get_record, get_txt, get_txtbind,
                        parse_dmarc, parse_spf)
from .geoip_utils import annotate_geoip, init_geoip
from .web_utils import get_webserver_info
from .mail_utils import get_mx_info


config = load_config("config.yml")
geoip_dbs = init_geoip(config)
local_resolver = get_local_resolver(config)


def get_dns_local(domain):
    txt = get_record(domain, "TXT", local_resolver)
    return {
        "NS_AUTH": get_record(domain, "NS", local_resolver),
        "MAIL": get_record(domain, "MX", local_resolver),
        "WEB4": annotate_geoip(get_record(domain, "A", local_resolver), "value", geoip_dbs),
        "WEB4_www": annotate_geoip(get_record("www." + domain, "A", local_resolver), "value", geoip_dbs),
        "WEB6": annotate_geoip(get_record(domain, "AAAA", local_resolver), "value", geoip_dbs),
        "WEB6_www": annotate_geoip(get_record("www." + domain, "AAAA", local_resolver), "value", geoip_dbs),
        "WEB_TLSA": get_record("_443._tcp." + domain, "TLSA", local_resolver),
        "WEB_TLSA_www": get_record("_443._tcp.www." + domain, "TLSA", local_resolver),
        "MAIL_TLSA": get_record("_25._tcp." + domain, "TLSA", local_resolver),
        "TXT": txt,
        "TXT_SPF": parse_spf(get_txt(re.compile("^\"?v=spf"), deepcopy(txt), "value"), "value"),
        "TXT_DMARC": parse_dmarc(get_record("_dmarc." + domain, "TXT", local_resolver), "value"),
        "DS": annotate_dns_algorithm(get_record(domain, "DS", local_resolver), "value", 1),
        "DNSKEY": annotate_dns_algorithm(get_record(domain, "DNSKEY", local_resolver), "value", 2),
        "DNSSEC": check_dnssec(domain, local_resolver),
    }


def get_dns_auth(domain, nameservers):
    timeout = config["timeouts"]["dns"]
    if not nameservers or len(nameservers) < 1:
        return None
    results = []
    for item in nameservers:
        ns = item["value"]
        if not ns:
            continue
        a = get_record(ns, "A", local_resolver)
        aaaa = get_record(ns, "AAAA", local_resolver)
        ns_ipv4 = a[0]["value"] if a else None
        ns_ipv6 = aaaa[0]["value"] if aaaa else None
        result = {
            "ns": ns,
            "ns_ipv4": annotate_geoip([{"value": ns_ipv4}], "value", geoip_dbs)[0] if ns_ipv4 else ns_ipv4,
            "ns_ipv6": annotate_geoip([{"value": ns_ipv6}], "value", geoip_dbs)[0] if ns_ipv6 else ns_ipv6,
            "HOSTNAMEBIND4": get_txtbind(ns_ipv4, "hostname.bind", timeout) if ns_ipv4 else None,
            "HOSTNAMEBIND6": get_txtbind(ns_ipv6, "hostname.bind", timeout) if ns_ipv6 else None,
            "VERSIONBIND4": get_txtbind(ns_ipv4, "version.bind", timeout) if ns_ipv4 else None,
            "VERSIONBIND6": get_txtbind(ns_ipv6, "version.bind", timeout) if ns_ipv6 else None,
        }
        results.append(result)
    return results


def get_web_status(domain, dns):
    return {
        "WEB4_80": get_webserver_info(domain, dns["WEB4"], config),
        "WEB4_80_www": get_webserver_info(f"www.{domain}", dns["WEB4"], config),
        "WEB4_443": get_webserver_info(domain, dns["WEB4"], config, tls=True),
        "WEB4_443_www": get_webserver_info(f"www.{domain}", dns["WEB4"], config, tls=True),
        "WEB6_80": get_webserver_info(domain, dns["WEB6"], config, ipv6=True),
        "WEB6_80_www": get_webserver_info(f"www.{domain}", dns["WEB6"], config, ipv6=True),
        "WEB6_443": get_webserver_info(domain, dns["WEB6"], config,  ipv6=True, tls=True),
        "WEB6_443_www": get_webserver_info(f"www.{domain}", dns["WEB6"], config, ipv6=True, tls=True)
    }


def process_domain(domain):
    dns_local = get_dns_local(domain)
    dns_auth = get_dns_auth(domain, dns_local["NS_AUTH"])
    mail = get_mx_info(dns_local["MAIL"], config["timeouts"]["mail"], local_resolver)
    web = get_web_status(domain, dns_local)

    return {
        "domain": domain,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "results": {
            "DNS_LOCAL": dns_local,
            "DNS_AUTH": dns_auth,
            "MAIL": mail,
            "WEB": web
        }
    }


def get_json_result(domain):
    return json.dumps(process_domain(domain), ensure_ascii=False, check_circular=False, separators=(",", ":"))
