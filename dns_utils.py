import dns.resolver


def get_local_resolver(config):
    use_custom_dns = "dns" in config and len(config["dns"]) > 0

    local_resolver = dns.resolver.Resolver(configure=(not use_custom_dns))
    local_resolver.timeout = local_resolver.lifetime = int(config["DNS_TIMEOUT"])
    if use_custom_dns:
        local_resolver.nameservers = config["dns"]
    return local_resolver


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
