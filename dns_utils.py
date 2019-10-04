import dns.resolver
import dns.name
import dns.dnssec


def get_local_resolver(config):
    use_custom_dns = "dns" in config and len(config["dns"]) > 0

    local_resolver = dns.resolver.Resolver(configure=(not use_custom_dns))
    local_resolver.timeout = local_resolver.lifetime = int(config["DNS_TIMEOUT"])
    if use_custom_dns:
        local_resolver.nameservers = config["dns"]
    return local_resolver


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

    if rcode != 0:  # NOERROR
        return {"valid": None, "error": f"rcode {rcode}"}

    answer = response.answer

    if len(answer) != 2:  # no DNSSEC records
        return {"valid": None}

    if answer[0].rdtype == dns.rdatatype.RRSIG:
        rrsig, rrset = answer
    elif answer[1].rdtype == dns.rdatatype.RRSIG:
        rrset, rrsig = answer
    else:
        return {"valid": None, "error": "something weird happened"}
    keys = {sub: rrset}

    try:
        dns.dnssec.validate(rrset, rrsig, keys)
    except Exception as e:
        return {"valid": False, "message": str(e)}
    return {"valid": True, "rrsig": str(rrsig), "rrset": str(rrset)}


def annotate_dns_algorithm(items, key, index):
    if items:
        for item in items:
            alg_number = item[key].split()[index]
            item["algorithm"] = dns.dnssec.algorithm_to_text(int(alg_number))
    return items


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


def get_record(domain, record, resolver):
    results = []
    try:
        answers = resolver.query(domain, record, rdclass="IN")
        for item in answers:
            results.append({"value": str(item)})
    except (
        dns.resolver.NoAnswer,
        dns.rdatatype.UnknownRdatatype,
        dns.resolver.NoNameservers,
        dns.resolver.NXDOMAIN,
        dns.exception.Timeout,
    ):
        pass
    if len(results) > 0:
        return results
    else:
        return None
