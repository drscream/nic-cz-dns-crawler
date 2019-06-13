# `dns-crawler`

> Crawler for getting info about a huge number of DNS domains


## Installation

### Requirements

- Python 3.6+
- [rq](https://python-rq.org/)
- [redis](https://redis.io/)
- [requests](https://python-requests.org/)
- [dnspython](http://www.dnspython.org/)
- [geoip2](https://geoip2.readthedocs.io/en/latest/) + up-to-date Country and ISP (or ASN) databases (mmdb format)

### Redis confinguration

No special config needed, but increase memory limit if you have a lot of domains to process (`maxmemory 1G`). You can also disable disk snapshots to save some I/O time (comment out `save …` lines).

### Installing Python deps in a virtualenv

```
$ git clone https://gitlab.labs.nic.cz/adam/dns-crawler
$ cd dns-crawler
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt 
```

### Trying it out

Create a short domain list (one 2nd level domain per line):

```
$ echo "nic.cz\nnetmetr.cz\nroot.cz" > domains.txt
```

Start the main process to create job for every domain:

```
$ python ./main.py domains.txt
[2019-05-03 11:45:59] Created 3 jobs.
[2019-05-03 11:45:59] 0/3
[2019-05-03 11:46:01] 0/3
```

Now it waits for workers to take the jobs from redis. Run a worker in another shell:

```
$ python workers.py 1
11:48:17 RQ worker 'rq:worker:foo-2' started, version 1.0
11:48:17 *** Listening on default...
11:48:17 Cleaning registries for queue: default
11:48:17 default: crawl.process_domain('nic.cz') (nic.cz)
11:48:17 RQ worker 'rq:worker:foo-1' started, version 1.0
11:48:17 RQ worker 'rq:worker:foo-3' started, version 1.0
11:48:17 *** Listening on default...
11:48:17 *** Listening on default...
11:48:17 default: crawl.process_domain('netmetr.cz') (netmetr.cz)
11:48:17 default: crawl.process_domain('root.cz') (root.cz)
11:48:17 default: Job OK (netmetr.cz)
11:48:17 default: Job OK (nic.cz)
11:48:17 RQ worker 'rq:worker:foo-2' done, quitting
11:48:17 RQ worker 'rq:worker:foo-3' done, quitting
11:48:19 default: Job OK (root.cz)
```

Results are printed to the main process' stdout – JSON for every domain, separated by `\n`:

```
…
[2019-05-03 11:48:17] 2/3
{"domain": "netmetr.cz", "DNS_LOCAL": {"DNS_AUTH": ["a.ns.nic.cz.", "b.ns.nic.cz.", "d.ns.nic.cz."], "MAIL": ["10 mail.nic.cz.", "15 mx.nic.cz.", "20 bh.nic.cz."], "WEB4": [{"ip": "217.31.192.130", "geoip": {"country": "CZ", "asn": 25192, "org": "CZ.NIC, z.s.p.o."}}], "WEB4_www": [{"ip": "217.31.192.130", "geoip": {"country": "CZ", "asn": 25192, "org": "CZ.NIC, z.s.p.o."}}], "WEB6": [{"ip": "2001:1488:ac15:ff90::130", "geoip": {"country": "CZ", "asn": 25192, "org": "CZ.NIC, z.s.p.o."}}], "WEB6_www": [{"ip": "2001:1488:ac15:ff90::130", "geoip": {"country": "CZ", "asn": 25192, "org": "CZ.NIC, z.s.p.o."}}], "WEB_TLSA": null, "WEB_TLSA_www": null, "MAIL_TLSA": null, "DS": ["54959 13 2 f378137545d35b2297be8ef5542e72763e0c47c520ef3a0ec894f39ad7679a0a"], "DNSKEY": ["256 3 13 36WIaijhhLkLtG77ecHTuA/rODUNy9kj J5c2QVUZYMtBsg/SDc3e+n+bxYZyTE3t wnXa/6hyAyIGjCx4nJQwQQ==", "257 3 13 KDAJfPGWgvNAEHUMzmmSa+c3gHfoGIsX nhIO1iAYGTAyVBo+CLTyIk3wxDtt4Yn3 eCrCiYsEAHBJgQvA3pwJ8w=="]}, "DNS_AUTH": [{"ns": "a.ns.nic.cz.", "ns_ipv4": [{"ip": "194.0.12.1", "geoip": {"country": "CZ", "asn": 25192, "org": "CZ.NIC, z.s.p.o."}}], "ns_ipv6": [{"ip": "2001:678:f::1", "geoip": {"country": "UA", "asn": 25192, "org": "CZ.NIC, z.s.p.o."}}], "HOSTNAMEBIND4": {"value": null, "error": "The DNS response does not contain an answer to the question: hostname.bind. CH TXT"}, "HOSTNAMEBIND6": {"value": null, "error": "All nameservers failed to answer the query hostname.bind. CH TXT: Server 2001:678:f::1 UDP port 53 answered REFUSED"}, "VERSIONBIND4": {"value": null, "error": "The DNS response does not contain an answer to the question: version.bind. CH TXT"}, "VERSIONBIND6": {"value": null, "error": "All nameservers failed to answer the query version.bind. CH TXT: Server 2001:678:f::1 UDP port 53 answered REFUSED"}}, {"ns": "b.ns.nic.cz.", "ns_ipv4": [{"ip": "194.0.13.1", "geoip": {"country": "CZ", "asn": 25192, "org": "CZ.NIC, z.s.p.o."}}], "ns_ipv6": [{"ip": "2001:678:10::1", "geoip": {"country": "UA", "asn": 25192, "org": "CZ.NIC, z.s.p.o."}}], "HOSTNAMEBIND4": {"value": null, "error": "The DNS resp
onse does not contain an answer to the question: hostname.bind. CH TXT"}, "HOSTNAMEBIND6": {"value": null, "error": "All nameservers failed to answer the query h
ostname.bind. CH TXT: Server 2001:678:10::1 UDP port 53 answered REFUSED"}, "VERSIONBIND4": {"value": null, "error": "The DNS response does not contain an answer
 to the question: version.bind. CH TXT"}, "VERSIONBIND6": {"value": null, "error": "All nameservers failed to answer the query version.bind. CH TXT: Server 2001:
678:10::1 UDP port 53 answered REFUSED"}}, {"ns": "d.ns.nic.cz.", "ns_ipv4": [{"ip": "193.29.206.1", "geoip": {"country": "CZ", "asn": 25192, "org": "CZ.NIC, z.s
.p.o."}}], "ns_ipv6": [{"ip": "2001:678:1::1", "geoip": {"country": "UA", "asn": 25192, "org": "CZ.NIC, z.s.p.o."}}], "HOSTNAMEBIND4": {"value": null, "error": "
All nameservers failed to answer the query hostname.bind. CH TXT: Server 193.29.206.1 UDP port 53 answered REFUSED"}, "HOSTNAMEBIND6": {"value": null, "error": "
The DNS response does not contain an answer to the question: hostname.bind. CH TXT"}, "VERSIONBIND4": {"value": null, "error": "The DNS response does not contain
 an answer to the question: version.bind. CH TXT"}, "VERSIONBIND6": {"value": null, "error": "All nameservers failed to answer the query version.bind. CH TXT: Se
rver 2001:678:1::1 UDP port 53 answered REFUSED"}}], "WEB": {"WEB4_80_VENDOR": {"value": "nginx"}, "WEB4_80_www_VENDOR": {"value": "nginx"}, "WEB6_80_VENDOR": {"
value": "nginx"}, "WEB6_80_www_VENDOR": {"value": "nginx"}}}
…
```

The progress info with timestamp is printed to stderr, so you can save the output easily – `python main.py list.txt > result`.

If you want formatted JSONs, just pipe the output through [jq](https://stedolan.github.io/jq/): `python main.py list.txt | jq`.

## Config file

GeoIP DB paths, DNS resolver IP(s), and timeouts are read from `config.yml`. The default values are:

```yaml
geoip:
  country: /usr/share/GeoIP/GeoIP2-Country.mmdb
  isp: /usr/share/GeoIP/GeoIP2-ISP.mmdb
dns:
  - 127.0.0.1
DNS_TIMEOUT: 2
HTTP_TIMEOUT: 2
```

Using free (GeoLite2) Country and ASN DBs instead of commercial ones:

```yaml
geoip:
  country: /usr/share/GeoIP/GeoLite2-Country.mmdb
  asn: /usr/share/GeoIP/GeoLite2-ASN.mmdb
```

`ISP` (paid) database is preffered over `ASN` (free), if both are defined. The difference is described on Maxmind's website: https://dev.maxmind.com/faq/what-is-the-difference-between-the-geoip-isp-and-organization-databases/.

The free `GeoLite2-Country` seems to be a bit inaccurate, especially for IPv6 (it places some CZ.NIC nameservers in Ukraine etc.).

Using [ODVR](https://blog.nic.cz/2019/04/30/spoustime-nove-odvr/) or other resolvers:

```yaml
dns:
  - 193.17.47.1
  - 185.43.135.1
```

If no resolvers are specified (`dns` is missing or empty in the config file), the crawler will attempt to use system settings (`/etc/resolv.conf` on Linux).

## Command line parameters

### main.py

```
main.py <file>
       file - plaintext domain list, one domain per line (separated by \n)
```

### workers.py

```
Usage: workers.py [count] [redis]
       count - worker count, 8 workers per CPU core by default
       redis - redis host, localhost:6379 by default

Examples: workers.py 8
          workers.py 24 192.168.0.22:4444
          workers.py 16 redis.foo.bar
```

## Running on multiple machines

Since all communication between the main process and workers is done through Redis, it's easy to scale the crawler to any number of machines:

```
server-1                     server-2
┬──────────────────┐         ┬──────────────────┐
│     main.py      │         │     workers.py   │
│        +         │ ------- │        +         │
│      redis       │         │    DNS resolver  │
└──────────────────┘         └──────────────────┘

                             server-3
                             ┬──────────────────┐
                             │     workers.py   │
                     ------- │        +         │
                             │    DNS resolver  │
                             └──────────────────┘

                             …
                             …

                             server-n
                             ┬──────────────────┐
                             │     workers.py   │
                     _______ │        +         │
                             │    DNS resolver  │
                             └──────────────────┘
```

Just tell the workers to connect to the shared Redis on the main server, eg.:

```
$ python workers.py 24 192.168.0.2:6379
```

## Monitoring

### Command line

```
$ rq info
default      |████████████████████ 219458
1 queues, 219458 jobs total

0 workers, 1 queues
```

### Web interface

```
$ pip install rq-dashboard
$ rq-dashboard
RQ Dashboard version 0.4.0                                                 
 * Serving Flask app "rq_dashboard.cli" (lazy loading)                            
 * Environment: production                                                
   WARNING: Do not use the development server in a production environment. 
   Use a production WSGI server instead.                                          
 * Debug mode: off                            
 * Running on http://0.0.0.0:9181/ (Press CTRL+C to quit)
 ```

 ![RQ Dashboard screenshot](https://i.vgy.me/sk7zWa.png)

 ![RQ Dashboard screenshot](https://i.vgy.me/4y5Zee.png)

## Tests

Some basic tests are in the `tests` directory in this repo. If you want to run them manually, take a look at the `test`  job in `.gitlab-ci.yml` – basically it just downloads free GeoIP DBs, tells the crawler to use them, and crawles some domains, checking values in JSON output.