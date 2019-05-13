import requests
import dns.resolver
import urllib3
import geoip2.database
import yaml
from os import path

pwd = path.dirname(__file__)

with open(path.join(pwd, "config.yml"), "r") as conf_file:
    config = yaml.load(conf_file, Loader=yaml.BaseLoader)

geoip_country = None
geoip_isp = None
geoip_asn = None

if "country" in config["geoip"]:
    geoip_country = geoip2.database.Reader(path.join(pwd, config["geoip"]["country"]))

if "isp" in config["geoip"]:
    geoip_isp = geoip2.database.Reader(path.join(pwd, config["geoip"]["isp"]))

if "asn" in config["geoip"]:
    geoip_asn = geoip2.database.Reader(path.join(pwd, config["geoip"]["asn"]))

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DNS_TIMEOUT = int(config["DNS_TIMEOUT"])
HTTP_TIMEOUT = int(config["HTTP_TIMEOUT"])

local_resolver = dns.resolver.Resolver(configure=False)
local_resolver.nameservers = config["dns"]
local_resolver.timeout = local_resolver.lifetime = DNS_TIMEOUT


def get_geoip(ip):
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
    return result


def get_record(domain, record, geoip=False):
    results = []
    try:
        answers = local_resolver.query(domain, record, rdclass="IN")
        for item in answers:
            if not geoip:
                results = results + [str(item)]
            else:
                ip = str(item)
                results = results + [{"ip": ip, "geoip": get_geoip(ip)}]
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


def get_dns_local(domain):
    return {
        "DNS_AUTH": get_record(domain, "NS"),
        "MAIL": get_record(domain, "MX"),
        "WEB4": get_record(domain, "A", geoip=True),
        "WEB4_www": get_record("www." + domain, "A", geoip=True),
        "WEB6": get_record(domain, "AAAA", geoip=True),
        "WEB6_www": get_record("www." + domain, "AAAA", geoip=True),
        "WEB_TLSA": get_record("_443._tcp." + domain, "TLSA"),
        "WEB_TLSA_www": get_record("_443._tcp.www." + domain, "TLSA"),
        "MAIL_TLSA": get_record("_25._tcp." + domain, "TLSA"),
        "DS": get_record(domain, "DS"),
        "DNSKEY": get_record(domain, "DNSKEY"),
    }


def get_txtbind(nameserver, qname):
    result = None
    try:
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = [nameserver]
        resolver.timeout = resolver.lifetime = DNS_TIMEOUT
        answers = resolver.query(qname, rdtype="TXT", rdclass="CHAOS")
        result = {"value": str(answers[0]).replace('"', "")}
    except Exception as e:
        result = {"value": None, "error": str(e)}
    return result


def get_dns_auth(domain, nameservers):
    if not nameservers or len(nameservers) < 1:
        return None
    results = []
    for ns in nameservers:
        ns_ipv4 = get_record(ns, "A", geoip=True)
        ns_ipv6 = get_record(ns, "AAAA", geoip=True)
        result = {
            "ns": ns,
            "ns_ipv4": ns_ipv4,
            "ns_ipv6": ns_ipv6,
            "HOSTNAMEBIND4": get_txtbind(ns_ipv4[0]["ip"], "hostname.bind") if ns_ipv4 else None,
            "HOSTNAMEBIND6": get_txtbind(ns_ipv6[0]["ip"], "hostname.bind") if ns_ipv6 else None,
            "VERSIONBIND4": get_txtbind(ns_ipv4[0]["ip"], "version.bind") if ns_ipv4 else None,
            "VERSIONBIND6": get_txtbind(ns_ipv6[0]["ip"], "version.bind") if ns_ipv6 else None,
        }
        results.append(result)
    return results


def get_vendor(domain, ips, ipv6=False, tls=False):
    if not ips or len(ips) < 1:
        return None
    if tls:
        protocol = "https"
        port = 443
    else:
        protocol = "http"
        port = 80
    if not ipv6:
        host = ips[0]["ip"]
    else:
        host = f"[{ips[0]['ip']}]"
    try:
        r_head = requests.head(
            f"{protocol}://{host}:{port}/",
            timeout=HTTP_TIMEOUT,
            headers={"Host": domain},
            verify=False,
        )
    except Exception as e:
        return {"value": None, "error": str(e)}
    if "server" in r_head.headers:
        return {"value": r_head.headers["server"]}
    else:
        return None


def get_web_status(domain, dns):
    # if len(dns.WEB4) > 1:
    result = {
        "WEB4_80_VENDOR": get_vendor(domain, dns["WEB4"]),
        "WEB4_80_www_VENDOR": get_vendor(f"www.{domain}", dns["WEB4"]),
        # "WEB4_443_VENDOR": get_vendor(domain, dns["WEB4"], tls=True),
        # "WEB4_443_www_VENDOR": get_vendor(f"www.{domain}", dns["WEB4"], tls=True),
        "WEB6_80_VENDOR": get_vendor(domain, dns["WEB6"], ipv6=True),
        "WEB6_80_www_VENDOR": get_vendor(f"www.{domain}", dns["WEB6"], ipv6=True),
        # "WEB6_443_VENDOR": get_vendor(domain, dns["WEB6"], ipv6=True, tls=True),
        # "WEB6_443_www_VENDOR": get_vendor(f"www.{domain}", dns["WEB6"], ipv6=True, tls=True)
    }
    # except requests.exceptions.ConnectionError:
    #     print(f"No address associated with www.{domain}")
    # except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
    #     print(f"Timeout: {url}")

    # result["WEB4_80_www_VENDOR"] = r_head.headers["server"]
    return result


def process_domain(domain):
    result = {"domain": domain}
    dns_local = get_dns_local(domain)
    dns_auth = get_dns_auth(domain, dns_local["DNS_AUTH"])
    web = get_web_status(domain, dns_local)
    result = {**result, "DNS_LOCAL": dns_local, "DNS_AUTH": dns_auth, "WEB": web}

    return result
