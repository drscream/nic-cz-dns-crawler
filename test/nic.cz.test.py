from crawl import process_domain
import json

r = process_domain("nic.cz")

print(json.dumps(r))

assert r["results"]["DNS_LOCAL"]["DNS_AUTH"] == [
    {"value": "a.ns.nic.cz."},
    {"value": "b.ns.nic.cz."},
    {"value": "d.ns.nic.cz."}
]

assert r["results"]["WEB"]["WEB4_80_VENDOR"][0]["value"] == "nginx"
assert r["results"]["DNS_LOCAL"]["WEB4"][0]["ripe"]["netname"] == "CZ-NIC-I"
assert r["results"]["DNS_LOCAL"]["DNSSEC"]["valid"]
assert r["results"]["DNS_LOCAL"]["DS"][0]["algorithm"] == "ECDSAP256SHA256"
assert r["results"]["DNS_LOCAL"]["WEB4"][0]["geoip"] == {
    "country": "CZ",
    "asn": 25192,
    "org": "CZ.NIC, z.s.p.o.",
}
