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
import re

import dns.dnssec
import dns.name
import dns.resolver

from .geoip_utils import annotate_geoip


def get_local_resolver(config):
    dns_timeout = config["timeouts"]["dns"]
    use_custom_dns = "dns" in config and len(config["dns"]["resolvers"]) > 0

    local_resolver = dns.resolver.Resolver(configure=(not use_custom_dns))
    local_resolver.timeout = local_resolver.lifetime = dns_timeout
    if use_custom_dns:
        local_resolver.nameservers = config["dns"]["resolvers"]
    return local_resolver


def validate_rrset(rrset, rrsigset, keys, origin=None, now=None):
    if isinstance(origin, str):
        origin = dns.name.from_text(origin, dns.name.root)

    if isinstance(rrset, tuple):
        rrname = rrset[0]
    else:
        rrname = rrset.name

    if isinstance(rrsigset, tuple):
        rrsigname = rrsigset[0]
        rrsigrdataset = rrsigset[1]
    else:
        rrsigname = rrsigset.name
        rrsigrdataset = rrsigset

    rrname = rrname.choose_relativity(origin)
    rrsigname = rrsigname.choose_relativity(origin)
    if rrname != rrsigname:
        raise dns.dnssec.ValidationFailure("owner names do not match")

    messages = []
    for rrsig in rrsigrdataset:
        try:
            dns.dnssec._validate_rrsig(rrset, rrsig, keys, origin, now)
            return
        except dns.dnssec.ValidationFailure as e:
            messages.append(str(e))
    raise dns.dnssec.ValidationFailure(messages[-1])


def check_dnssec(domain, resolver):
    dnsname = dns.name.from_text(domain)
    depth = dnsname.__len__()
    sub = (dnsname.split(depth=depth))[1]
    q = dns.message.make_query(sub, "DNSKEY", want_dnssec=True)
    try:
        response = dns.query.udp(q, resolver.nameservers[0], resolver.timeout, ignore_unexpected=True)
    except dns.exception.Timeout:
        return {"valid": None, "error": "timeout"}
    except dns.message.Truncated:
        try:
            response = dns.query.tcp(q, resolver.nameservers[0], resolver.timeout)
        except dns.exception.Timeout:
            return {"valid": None, "error": "timeout"}

    rcode = response.rcode()

    if rcode == 2:  # NOERROR
        return {"valid": False, "message": f"rcode {rcode}"}

    if rcode != 0:  # NOERROR
        return {"valid": None, "message": f"rcode {rcode}"}

    answer = response.answer

    if len(answer) == 0:  # no DNSSEC records
        return {"valid": None, "message": "No records"}

    if len(answer) == 1:  # missing DS or DNSKEY
        if "DNSKEY" in repr(answer[0]):
            return {"valid": None, "message": "Missing DS"}
        elif "DS" in repr(answer[0]):
            return {"valid": None, "message": "Missing DNSKEY"}
        else:
            return {"valid": None, "message": f"Missing DS or DNSKEY, answer contains: '{answer[0]}'."}

    try:
        if answer[0].rdtype == dns.rdatatype.RRSIG:
            rrsig, rrset = answer
        elif answer[1].rdtype == dns.rdatatype.RRSIG:
            rrset, rrsig = answer
        else:
            return {"valid": None, "error": "something weird happened"}
    except ValueError as e:
        return {"valid": None, "error": str(e)}

    keys = {sub: rrset}

    try:
        validate_rrset(rrset, rrsig, keys)
    except Exception as e:
        return {"valid": False, "error": str(e)}
    return {"valid": True, "rrsig": str(rrsig).split("\n")}


def annotate_dns_algorithm(items, index, key="value"):
    if items:
        for item in items:
            if not item[key]:
                continue
            try:
                alg_number = item[key].split()[index]
            except IndexError:
                continue
            item["algorithm"] = dns.dnssec.algorithm_to_text(int(alg_number))
    return items


def parse_dmarc(items, key="value"):
    if not items:
        return None
    items = [item for item in items if item[key] and item[key].startswith('"v=DMARC')]
    if len(items) == 0:
        return None
    parsed = []
    for item in items:
        record = item[key].strip('"').strip(" ")
        raw_tags = [t.split("=") for t in record.split(";") if t]
        output = {t[0].strip(): t[1].strip() for t in raw_tags if len(t) >= 2}
        item = {k: v for k, v in output.items() if v is not None}
        parsed.append(item)
    if len(parsed) == 0:
        return None
    return parsed


def get_spf_ips(record, protocol):
    key = f"ip{str(protocol)}:"
    ips = [f.replace(key, "") for f in record if f.startswith(key)]
    if len(ips) == 0:
        return None
    return ips


def get_spf_includes(record):
    key = "include:"
    includes = [f.replace(key, "") for f in record if f.startswith(key)]
    if len(includes) == 0:
        return None
    return includes


def get_spf_rules(record):
    return record[1:]


def get_spf_all(record):
    alls = [k for k in record if "all" in k]
    if len(alls) == 0:
        return None
    else:
        all = alls[-1]
        if all == "all":
            all = "+all"
        return all.replace("all", "")


def parse_spf(items, key="value"):
    if not items:
        return None
    items = [item for item in items if item[key] and item[key].startswith('"v=spf')]
    if len(items) == 0:
        return None
    parsed = []
    for item in items.copy():
        output = {}
        record = re.sub(r" +", " ", item[key].strip('"')).split(" ")
        kvs = [k for k in record if "=" in k]
        for kv in kvs:
            data = kv.split("=")
            output[data[0]] = data[1]
        output["rules"] = get_spf_rules(record)
        output["ip4"] = get_spf_ips(record, 4)
        output["ip6"] = get_spf_ips(record, 6)
        output["include"] = get_spf_includes(record)
        output["all"] = get_spf_all(record)
        item = {k: v for k, v in output.items() if v is not None}
        parsed.append(item)
    if len(parsed) == 0:
        return None
    return parsed


def parse_tlsa(items, key="value"):
    if not items:
        return None
    parsed = []
    for item in items:
        if not item[key]:
            continue
        output = {}
        fields = item[key].split(" ")
        output["usage"] = int(fields[0])
        output["selector"] = int(fields[1])
        output["matchingtype"] = int(fields[2])
        output["data"] = fields[3]
        item = {k: v for k, v in output.items() if v is not None}
        parsed.append(item)
    if len(parsed) == 0:
        return None
    return parsed


def get_txt(regex, items, key="value"):
    if not items:
        return items
    filtered = []
    for item in items:
        if item[key] and re.match(regex, item[key]):
            filtered.append(item)
    if len(filtered) == 0:
        return None
    return filtered


def get_chaostxt(nameserver, qname, timeout):
    result = None
    try:
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = [nameserver]
        resolver.timeout = timeout
        resolver.lifetime = timeout
        answers = resolver.query(qname, rdtype="TXT", rdclass="CHAOS", lifetime=timeout)
        answers_l = []
        for answer in answers:
            answers_l.append(str(answer).replace('"', ""))
        result = {"value": answers_l}
    except Exception as e:
        result = {"value": None, "error": str(e)}
    return result


def get_ns_info(ip, chaosrecords, geoip_dbs, timeout, cache_timeout, redis):
    cache_key = f"cache-ns-{ip['value']}"
    if redis is not None:
        cached = redis.get(cache_key)
        if cached is not None:
            redis.expire(cache_key, cache_timeout)
            return json.loads(cached.decode("utf-8"))
    if ip["value"] is None:
        return None
    geoip = annotate_geoip([ip], geoip_dbs)[0]
    result = {
        "ip": ip["value"],
        "geoip": geoip["geoip"] if "geoip" in geoip else None
    }
    for record in chaosrecords:
        result[record.replace(".", "")] = get_chaostxt(ip["value"], record, timeout)
    if redis is not None:
        redis.set(cache_key, json.dumps(result), ex=cache_timeout)
    return result


def value_from_record(record, data):
    return re.sub(r".*" + re.escape(record) + " ", "", data)


def get_record(domain_name, record, resolver, protocol="udp", cname_count=None):
    results = []
    domain = dns.name.from_text(domain_name)
    if not domain.is_absolute():
        domain = domain.concatenate(dns.name.root)
    request = dns.message.make_query(domain, record)
    request.flags |= dns.flags.CD
    try:
        response = getattr(dns.query, protocol)(request, resolver.nameservers[0], resolver.timeout)
    except (
        dns.query.UnexpectedSource,
        dns.query.BadResponse
    ):
        return get_record(domain_name, record, resolver)
    except (
        dns.resolver.NoAnswer,
        dns.rdatatype.UnknownRdatatype,
        dns.resolver.NoNameservers,
        dns.resolver.NXDOMAIN,
        dns.exception.Timeout,
    ):
        return None
    except dns.message.Truncated:
        return get_record(domain_name, record, resolver, protocol="tcp")
    for item in response.answer:
        if item.rdtype == dns.rdatatype.from_text(record) and item.name == domain:
            for line in str(item).split("\n"):
                results.append({"value": value_from_record(record, line)})
        elif item.rdtype == dns.rdatatype.from_text("CNAME"):
            for line in str(item).split("\n"):
                cname_domain = value_from_record("CNAME", line)
                results.append({
                    "cname": cname_domain,
                    "value": None
                })
        if item.rdtype == dns.rdatatype.from_text(record) and "cname" in results[-1]:
            for line in str(item).split("\n"):
                results.append({"value": value_from_record(record, line), "from_cname": str(item.name)})
    if len(results) > 0:
        return results
    else:
        return None


additional_parsers = {
    "SPF": parse_spf
}


def get_record_parser(record):
    try:
        parser = additional_parsers[record]
    except KeyError:
        parser = None
    return parser
