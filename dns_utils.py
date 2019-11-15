import dns.resolver
import dns.name
import dns.dnssec
import re


def get_local_resolver(config):
    use_custom_dns = "dns" in config and len(config["dns"]) > 0

    local_resolver = dns.resolver.Resolver(configure=(not use_custom_dns))
    local_resolver.timeout = local_resolver.lifetime = int(config["DNS_TIMEOUT"])
    if use_custom_dns:
        local_resolver.nameservers = config["dns"]
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
    sub = (dns.name.from_text(domain).split(depth=3))[1]
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
        return {"valid": None, "message": f"No records"}

    if len(answer) == 1:  # missing DS or DNSKEY
        if "DNSKEY" in repr(answer[0]):
            return {"valid": None, "message": f"Missing DS"}
        elif "DS" in repr(answer[0]):
            return {"valid": None, "message": f"Missing DNSKEY"}
        else:
            return {"valid": None, "message": f"Missing DS or DNSKEY, answer contains: '{answer[0]}'."}

    if answer[0].rdtype == dns.rdatatype.RRSIG:
        rrsig, rrset = answer
    elif answer[1].rdtype == dns.rdatatype.RRSIG:
        rrset, rrsig = answer
    else:
        return {"valid": None, "error": "something weird happened"}
    keys = {sub: rrset}

    try:
        validate_rrset(rrset, rrsig, keys)
    except Exception as e:
        return {"valid": False, "error": str(e)}
    return {"valid": True, "rrsig": str(rrsig).split("\n")}


def annotate_dns_algorithm(items, key, index):
    if items:
        for item in items:
            try:
                alg_number = item[key].split()[index]
            except IndexError:
                continue
            item["algorithm"] = dns.dnssec.algorithm_to_text(int(alg_number))
    return items


def parse_dmarc(items, key):
    if not items:
        return items
    parsed = []
    for item in items:
        record = item[key].strip("\"").strip(" ")
        raw_tags = [t.split("=") for t in record.split(';') if t]
        item[key] = {t[0].strip(): t[1].strip() for t in raw_tags}
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


def parse_spf(items, key):
    if not items:
        return items
    parsed = []
    for item in items.copy():
        dict = {}
        record = item[key].strip("\"").split(" ")
        alls = [k for k in record if "all" in k]
        if len(alls) == 0:
            all = None
        else:
            all = alls[0]
        kvs = [k for k in record if "=" in k]
        for kv in kvs:
            data = kv.split("=")
            dict[data[0]] = data[1]
        dict["ip4"] = get_spf_ips(record, 4)
        dict["ip6"] = get_spf_ips(record, 6)
        dict["include"] = get_spf_includes(record)
        dict["all"] = all
        item[key] = dict
        parsed.append(item)
    if len(parsed) == 0:
        return None
    return parsed


def get_txt(regex, items, key):
    if not items:
        return items
    filtered = []
    for item in items:
        if re.match(regex, item[key]):
            filtered.append(item)
    if len(filtered) == 0:
        return None
    return filtered


def get_txtbind(nameserver, qname, timeout=5):
    result = None
    try:
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = [nameserver]
        resolver.timeout = resolver.lifetime = timeout
        answers = resolver.query(qname, rdtype="TXT", rdclass="CHAOS")
        result = {"value": str(answers[0]).replace('"', "")}
    except Exception as e:
        result = {"value": None, "error": str(e)}
    return result


def value_from_record(record, data):
    if "CNAME" in data:
        record = "CNAME"
    return re.sub(r".*" + re.escape(record) + " ", "", data)


def get_record(domain, record, resolver):
    results = []
    domain = dns.name.from_text(domain)
    if not domain.is_absolute():
        domain = domain.concatenate(dns.name.root)
    request = dns.message.make_query(domain, record)
    request.flags |= dns.flags.CD
    try:
        response = dns.query.udp(request, resolver.nameservers[0])
    except dns.message.Truncated:
        response = dns.query.tcp(request, resolver.nameservers[0])
    except (
        dns.resolver.NoAnswer,
        dns.rdatatype.UnknownRdatatype,
        dns.resolver.NoNameservers,
        dns.resolver.NXDOMAIN,
        dns.exception.Timeout,
    ):
        pass
    for item in response.answer:
        for line in str(item).split("\n"):
            results.append({"value": value_from_record(record, line)})
    if len(results) > 0:
        return results
    else:
        return None
