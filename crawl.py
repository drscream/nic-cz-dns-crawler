from datetime import datetime
from config_loader import load_config
from geoip_utils import init_geoip, annotate_geoip
from http_utils import get_webserver_vendor
from dns_utils import get_local_resolver, get_txtbind, get_record, annotate_dns_algorithm, check_dnssec
from ripe_utils import annotate_ripe

config = load_config("config.yml")
geoip_dbs = init_geoip(config)
local_resolver = get_local_resolver(config)


def get_dns_local(domain):
    return {
        "DNS_AUTH": get_record(domain, "NS", local_resolver),
        "MAIL": get_record(domain, "MX", local_resolver),
        "WEB4": annotate_ripe(annotate_geoip(get_record(domain, "A", local_resolver), "value", geoip_dbs)),
        "WEB4_www":  annotate_ripe(annotate_geoip(get_record("www." + domain, "A", local_resolver), "value", geoip_dbs)),
        "WEB6":  annotate_ripe(annotate_geoip(get_record(domain, "AAAA", local_resolver), "value", geoip_dbs)),
        "WEB6_www":  annotate_ripe(annotate_geoip(get_record("www." + domain, "AAAA", local_resolver), "value", geoip_dbs)),
        "WEB_TLSA": get_record("_443._tcp." + domain, "TLSA", local_resolver),
        "WEB_TLSA_www": get_record("_443._tcp.www." + domain, "TLSA", local_resolver),
        "MAIL_TLSA": get_record("_25._tcp." + domain, "TLSA", local_resolver),
        "DS": annotate_dns_algorithm(get_record(domain, "DS", local_resolver), "value", 1),
        "DNSKEY": annotate_dns_algorithm(get_record(domain, "DNSKEY", local_resolver), "value", 2),
        "DNSSEC": check_dnssec(domain, local_resolver)
    }


def get_dns_auth(domain, nameservers):
    if not nameservers or len(nameservers) < 1:
        return None
    results = []
    for item in nameservers:
        ns = item["value"]
        ns_ipv4 = get_record(ns, "A", local_resolver)[0]["value"]
        ns_ipv6 = get_record(ns, "AAAA", local_resolver)[0]["value"]
        result = {
            "ns": ns,
            "ns_ipv4": annotate_ripe(annotate_geoip([{"value": ns_ipv4}], "value", geoip_dbs))[0],
            "ns_ipv6": annotate_ripe(annotate_geoip([{"value": ns_ipv6}], "value", geoip_dbs))[0],
            "HOSTNAMEBIND4": get_txtbind(ns_ipv4, "hostname.bind") if ns_ipv4 else None,
            "HOSTNAMEBIND6": get_txtbind(ns_ipv6, "hostname.bind") if ns_ipv6 else None,
            "VERSIONBIND4": get_txtbind(ns_ipv4, "version.bind") if ns_ipv4 else None,
            "VERSIONBIND6": get_txtbind(ns_ipv6, "version.bind") if ns_ipv6 else None,
        }
        results.append(result)
    return results


def get_web_status(domain, dns):
    result = {
        "WEB4_80_VENDOR": get_webserver_vendor(domain, dns["WEB4"]),
        "WEB4_80_www_VENDOR": get_webserver_vendor(f"www.{domain}", dns["WEB4"]),
        "WEB4_443_VENDOR": get_webserver_vendor(domain, dns["WEB4"], tls=True),
        "WEB4_443_www_VENDOR": get_webserver_vendor(f"www.{domain}", dns["WEB4"], tls=True),
        "WEB6_80_VENDOR": get_webserver_vendor(domain, dns["WEB6"], ipv6=True),
        "WEB6_80_www_VENDOR": get_webserver_vendor(f"www.{domain}", dns["WEB6"], ipv6=True),
        "WEB6_443_VENDOR": get_webserver_vendor(domain, dns["WEB6"], ipv6=True, tls=True),
        "WEB6_443_www_VENDOR": get_webserver_vendor(f"www.{domain}", dns["WEB6"], ipv6=True, tls=True)
    }
    return result


def process_domain(domain):
    dns_local = get_dns_local(domain)
    dns_auth = get_dns_auth(domain, dns_local["DNS_AUTH"])
    web = get_web_status(domain, dns_local)

    return {
        "domain": domain,
        "timestamp": datetime.utcnow().isoformat(),
        "results": {
            "DNS_LOCAL": dns_local,
            "DNS_AUTH": dns_auth,
            "WEB": web
        }
    }
