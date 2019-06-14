from crawl import process_domain
import json

r = process_domain("nic.cz")

print(json.dumps(r))
print()
print(r["DNS_LOCAL"]["DNS_AUTH"])

assert sorted(r["DNS_LOCAL"]["DNS_AUTH"]) == ["a.ns.nic.cz.", "b.ns.nic.cz.", "d.ns.nic.cz."]
assert r["WEB"]["WEB4_80_VENDOR"] == {"value": "nginx"}
assert r["DNS_LOCAL"]["WEB4"][0]["geoip"] == {
    "country": "CZ",
    "asn": 25192,
    "org": "CZ.NIC, z.s.p.o.",
}
