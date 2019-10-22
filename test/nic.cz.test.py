from crawl import process_domain
import json

r = process_domain("nic.cz")

print(json.dumps(r))


def sort_by_value(list):
    return sorted(list, key=lambda k: k["value"])


assert sort_by_value(r["results"]["DNS_LOCAL"]["NS_AUTH"]) == sort_by_value(
    [{"value": "a.ns.nic.cz."}, {"value": "b.ns.nic.cz."}, {"value": "d.ns.nic.cz."}]
)
assert r["results"]["WEB"]["WEB4_80"][0]["status"] == 301
assert r["results"]["WEB"]["WEB4_80"][0]["headers"]["server"][0] == "nginx"
assert r["results"]["WEB"]["WEB4_443"][0]["http2"]
assert r["results"]["WEB"]["WEB4_443_www"][0]["status"] == 200
assert r["results"]["DNS_LOCAL"]["DNSSEC"]["valid"]
assert r["results"]["DNS_LOCAL"]["DS"][0]["algorithm"] == "ECDSAP256SHA256"
assert r["results"]["DNS_LOCAL"]["WEB4"][0]["geoip"] == {"country": "CZ", "asn": 25192, "org": "CZ.NIC, z.s.p.o."}
