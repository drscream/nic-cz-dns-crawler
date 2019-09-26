# `dns-crawler`

> Crawler for getting info about *(possibly a huge number of)* DNS domains

## Basic usage

Feed domains into queue and wait for results:

```
$ python main.py domain-list.txt > result.json
```

(in another shell) Start workers which process the domains and return results to the main process:

```
$ python workers.py
```

## How fast is it anyway?

A single laptop on ~50Mbps connection can crawl the entire *.cz* zone overnight, give or take.

Since the crawler is designed to be parallel, the actual speed depends almost entirely on the worker count. And it can scale accross multiple machines almost infinitely, so should you need a million domains crawled in a few minutes, you can always just throw more hardware at it.

## Installation

### Requirements

- Python 3.6+
- [requests](https://python-requests.org/)
- [pyaml](https://pyyaml.org/) (for config loading)
- [dnspython](http://www.dnspython.org/) + [pycryptodome](https://pycryptodome.readthedocs.io/) & [python-ecdsa](https://github.com/warner/python-ecdsa) (for DNSSEC validation)
- [geoip2](https://geoip2.readthedocs.io/en/latest/) + up-to-date Country and ISP (or ASN) databases (mmdb format, works with both free and commercial ones)
- [rq](https://python-rq.org/) and [redis](https://redis.io/) if you want to process a huge number of domains and even run the crawler across multiple machines


### Redis configuration

No special config needed, but increase the memory limit if you have a lot of domains to process (eg. `maxmemory 1G`). You can also disable disk snapshots to save some I/O time (comment out the `save …` lines).

### Installing Python deps in a virtualenv

```
$ git clone https://gitlab.labs.nic.cz/adam/dns-crawler
$ cd dns-crawler
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt 
```

### Trying it out

Create a short domain list (one 2nd level domain per line):

```
$ echo "nic.cz\nnetmetr.cz\nroot.cz" > domains.txt
```

Start the main process to create job for every domain:

```
$ python main.py domains.txt
[2019-09-24 07:38:15] Reading domains from …/domains.txt.
[2019-09-24 07:38:15] Creating job queue using 2 threads.
[2019-09-24 07:38:15] 0/3 jobs created.
[2019-09-24 07:38:16] 3/3 jobs created.
[2019-09-24 07:38:16] Created 3 jobs. Waiting for workers…
[2019-09-24 07:38:17] 0/3
```

Now it waits for workers to take the jobs from redis. Run a worker in another shell:

```
$ python workers.py 1
07:38:17 RQ worker 'rq:worker:foo-2' started, version 1.0
07:38:17 *** Listening on default...
07:38:17 Cleaning registries for queue: default
07:38:17 default: crawl.process_domain('nic.cz') (nic.cz)
07:38:17 RQ worker 'rq:worker:foo-1' started, version 1.0
07:38:17 RQ worker 'rq:worker:foo-3' started, version 1.0
07:38:17 *** Listening on default...
07:38:17 *** Listening on default...
07:38:17 default: crawl.process_domain('netmetr.cz') (netmetr.cz)
07:38:17 default: crawl.process_domain('root.cz') (root.cz)
07:38:17 default: Job OK (netmetr.cz)
07:38:17 default: Job OK (nic.cz)
07:38:17 RQ worker 'rq:worker:foo-2' done, quitting
07:38:17 RQ worker 'rq:worker:foo-3' done, quitting
07:38:19 default: Job OK (root.cz)
```

### Output formats

Results are printed to the main process' stdout – JSON for every domain, separated by `\n`:

```
…
[2019-05-03 07:38:17] 2/3
{"domain": "nic.cz", "timestamp": "2019-09-24T05:28:06.536991", "results": {"DNS_LOCAL": {"DNS_AUTH": [{"value": "a.ns.nic.cz."}, {"value": "b.ns.nic.cz."}, {"value": "d.ns.nic.cz."}], "MAIL": [{"value": "10 mail.nic.cz."}, {"value": "20 mx.nic.cz."}, {"value": "30 bh.nic.cz."}], "WEB4": [{"value": "217.31.205.50", "geoip": {"country": "CZ", "org": "CZ.NIC, z.s.p.o.", "asn": 25192}, "ripe": {"netname": "CZ-NIC-I", "inetnum": "217.31.205.0 - 217.31.206.255"}}], "WEB4_www": [{"value": "217.31.205.50", "geoip": {"country": "CZ", "org": "CZ.NIC, z.s.p.o.", "asn": 25192}, "ripe": {"netname": "CZ-NIC-I", "inetnum": "217.31.205.0 - 217.31.206.255"}}], "WEB6": [{"value": "2001:1488:0:3::2", "geoip": {"country": "CZ", "org": "CZ.NIC, z.s.p.o.", "asn": 25192}, "ripe": {"netname": "CZ-NIC-NET", "inetnum": "2001:1488::/48"}}], "WEB6_www": [{"value": "2001:1488:0:3::2", "geoip": {"country": "CZ", "org": "CZ.NIC, z.s.p.o.", "asn": 25192}, "ripe": {"netname": "CZ-NIC-NET", "inetnum": "2001:1488::/48"}}], "WEB_TLSA": null, "WEB_TLSA_www": [{"value": "1 1 1 a1c442880eb3fdf5ea9978c3821b806520d39735cfa9fdfb0fc7b5c27c679db4"}], "MAIL_TLSA": null, "DS": [{"value": "61281 13 2 4104d40c8fe2030bf7a09a199fcf37b36f7ec8ddd16f5a84f2e61c248d3afd0f", "algorithm": "ECDSAP256SHA256"}], "DNSKEY": [{"value": "256 3 13 10TdB3LI+IdWr/LIV/0gntJWk14+7tzI L9Gpyvav3F8pjEhg0PB85k3ksXDfAZ/+ 9pxRXOou5nu68vUxkc0VbQ==", "algorithm": "ECDSAP256SHA256"}, {"value": "256 3 13 4BWL1uxEYld1r529eJRZ8vnCAWbbemDi A6QuJA5croqccrgSl11LpVl74RV66Tvx 4LqFpIuMD10oaTZDdHLbMg==", "algorithm": "ECDSAP256SHA256"}, {"value": "257 3 13 LM4zvjUgZi2XZKsYooDE0HFYGfWp242f KB+O8sLsuox8S6MJTowY8lBDjZD7JKbm aNot3+1H8zU9TrDzWmmHwQ==", "algorithm": "ECDSAP256SHA256"}], "DNSSEC": {"valid": true, "rrsig": "nic.cz. 260 IN RRSIG DNSKEY 13 2 1800 20191005212609 20190922054001 61281 nic.cz. Zdbi4HD79gLQ8fMX6aj2MqkavK30QFdy OhedI7zH/OZAund4ZnI/ri83S20fBeD0 uh1Gu2vKNY7y1KnegOJrfQ==\nnic.cz. 260 IN RRSIG DNSKEY 13 2 1800 20191005220333 20190922054001 41805 nic.cz. hqS71kiKr1tk0pl3rkh8WWmvBaOrbaZP PJm46gCf5jQkVfGwbBr9f337GNoWy8qZ ebBjEECssePwvhknOL6I4w==", "rrset": "nic.cz. 260 IN DNSKEY 256 3 13 10TdB3LI+IdWr/LIV/0gntJWk14+7tzI L9Gpyvav3F8pjEhg0PB85k3ksXDfAZ/+ 9pxRXOou5nu68vUxkc0VbQ==\nnic.cz. 260 IN DNSKEY 256 3 13 4BWL1uxEYld1r529eJRZ8vnCAWbbemDi A6QuJA5croqccrgSl11LpVl74RV66Tvx 4LqFpIuMD10oaTZDdHLbMg==\nnic.cz. 260 IN DNSKEY 257 3 13 LM4zvjUgZi2XZKsYooDE0HFYGfWp242f KB+O8sLsuox8S6MJTowY8lBDjZD7JKbm aNot3+1H8zU9TrDzWmmHwQ=="}}, "DNS_AUTH": [{"ns": "a.ns.nic.cz.", "ns_ipv4": {"value": "194.0.12.1", "geoip": {"country": "CZ", "org": "CZ.NIC, z.s.p.o.", "asn": 25192}, "ripe": {"netname": "A-NS-NIC-CZ", "inetnum": "194.0.12.0 - 194.0.12.255"}}, "ns_ipv6": {"value": "2001:678:f::1", "geoip": {"country": "DE", "org": "CZ.NIC, z.s.p.o.", "asn": 25192}, "ripe": {"netname": "A-NS-NIC-CZ", "inetnum": "2001:678:f::/48"}}, "HOSTNAMEBIND4": {"value": null, "error": "The DNS response does not contain an answer to the question: hostname.bind. CH TXT"}, "HOSTNAMEBIND6": {"value": null, "error": "All nameservers failed to answer the query hostname.bind. CH TXT: Server 2001:678:f::1 UDP port 53 answered REFUSED"}, "VERSIONBIND4": {"value": null, "error": "The DNS response does not contain an answer to the question: version.bind. CH TXT"}, "VERSIONBIND6": {"value": null, "error": "All nameservers failed to answer the query version.bind. CH TXT: Server 2001:678:f::1 UDP port 53 answered REFUSED"}}, {"ns": "b.ns.nic.cz.", "ns_ipv4": {"value": "194.0.13.1", "geoip": {"country": "CZ", "org": "CZ.NIC, z.s.p.o.", "asn": 25192}, "ripe": {"netname": "B-NS-NIC-CZ", "inetnum": "194.0.13.0 - 194.0.13.255"}}, "ns_ipv6": {"value": "2001:678:10::1", "geoip": {"country": "DE", "org": "CZ.NIC, z.s.p.o.", "asn": 25192}, "ripe": {"netname": "B-NS-NIC-CZ", "inetnum": "2001:678:10::/48"}}, "HOSTNAMEBIND4": {"value": null, "error": "The DNS response does not contain an answer to the question: hostname.bind. CH TXT"}, "HOSTNAMEBIND6": {"value": null, "error": "All nameservers failed to answer the query hostname.bind. CH TXT: Server 2001:678:10::1 UDP port 53 answered REFUSED"}, "VERSIONBIND4": {"value": null, "error": "The DNS response does not contain an answer to the question: version.bind. CH TXT"}, "VERSIONBIND6": {"value": null, "error": "All nameservers failed to answer the query version.bind. CH TXT: Server 2001:678:10::1 UDP port 53 answered REFUSED"}}, {"ns": "d.ns.nic.cz.", "ns_ipv4": {"value": "193.29.206.1", "geoip": {"country": "CZ", "org": "CZ.NIC, z.s.p.o.", "asn": 25192}, "ripe": {"netname": "D-NS-NIC-CZ", "inetnum": "193.29.206.0 - 193.29.206.255"}}, "ns_ipv6": {"value": "2001:678:1::1", "geoip": {"country": "DE", "org": "CZ.NIC, z.s.p.o.", "asn": 25192}, "ripe": {"netname": "D-NS-NIC-CZ", "inetnum": "2001:678:1::/48"}}, "HOSTNAMEBIND4": {"value": null, "error": "The DNS response does not contain an answer to the question: hostname.bind. CH TXT"}, "HOSTNAMEBIND6": {"value": null, "error": "The DNS response does not contain an answer to the question: hostname.bind. CH TXT"}, "VERSIONBIND4": {"value": null, "error": "The DNS response does not contain an answer to the question: version.bind. CH TXT"}, "VERSIONBIND6": {"value": null, "error": "The DNS response does not contain an answer to the question: version.bind. CH TXT"}}], "WEB": {"WEB4_80_VENDOR": [{"ip": "217.31.205.50", "value": "nginx"}], "WEB4_80_www_VENDOR": [{"ip": "217.31.205.50", "value": "nginx"}], "WEB4_443_VENDOR": [{"ip": "217.31.205.50", "value": "nginx"}], "WEB4_443_www_VENDOR": [{"ip": "217.31.205.50", "value": "nginx"}], "WEB6_80_VENDOR": [{"ip": "2001:1488:0:3::2", "value": "nginx"}], "WEB6_80_www_VENDOR": [{"ip": "2001:1488:0:3::2", "value": "nginx"}], "WEB6_443_VENDOR": [{"ip": "2001:1488:0:3::2", "value": "nginx"}], "WEB6_443_www_VENDOR": [{"ip": "2001:1488:0:3::2", "value": "nginx"}]}}}
…
```

The progress info with timestamp is printed to stderr, so you can save just the output easily – `python main.py list.txt > results`.

#### Formatting the JSON output

If you want formatted JSONs, just pipe the output through [jq](https://stedolan.github.io/jq/): `python main.py list.txt | jq`.

#### SQL output

An util to create SQL `INSERT`s from the crawler output is included in this repo.

```
$ python main.py list.txt | python output_sql.py table_name
INSERT INTO table_name VALUES …;
INSERT INTO table_name VALUES …;
```

You can even pipe it right into `psql` or another DB client, which will save the results into DB continually, as they come from the workers:

```
$ python main.py list.txt | python output_sql.py table_name | psql -d db_name …
```

It can also generate the table structure (`CREATE TABLE …`), taking the table name as a single argument (without piping anything to stdin):

```
$ python output_sql.py results
CREATE TABLE results …;
```

The SQL output is tested only with PostgreSQL 11.

#### Custom output formats

Since the main process just spits out JSONs to stdout, it's pretty easy to process it with almost anything.

A simple example for YAML output:

```python
import json
import yaml
import sys

for line in sys.stdin:
    print(yaml.dump(json.loads(line)))
```

(and then just `python main.py domains.txt | python yaml.py`)

CSV is a different beast, since there's no obvious way to represent arrays…

## Probing just a few domains (or a single one)

It's possible to run just the crawl function without the rq/redis/worker machinery, which could come handy if you're interested in just a small number of domains. To run it, just import the `process_domain` function.

Example:

```
$ python
>>> from crawl import process_domain
>>> result = process_domain("nic.cz")
>>> result
{'domain': 'nic.cz', 'timestamp': '2019-09-13T09:21:10.136303', 'results': { …
>>>
>>> result["results"]["DNS_LOCAL"]["DNS_AUTH"]
[{'value': 'a.ns.nic.cz.'}, {'value': 'b.ns.nic.cz.'}, {'value': 'd.ns.nic.cz.'}]
```

Formatted output, inline python code:

```
$ python -c "from crawl import process_domain; import json; print(json.dumps(process_domain('nic.cz'), indent=2))"
{
  "domain": "nic.cz",
  "timestamp": "2019-09-13T09:24:23.108941",
  "results": {
    "DNS_LOCAL": {
      "DNS_AUTH": [
        …
```


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

`ISP` (paid) database is preferred over `ASN` (free), if both are defined. The difference is described on Maxmind's website: https://dev.maxmind.com/faq/what-is-the-difference-between-the-geoip-isp-and-organization-databases/.

The free `GeoLite2-Country` seems to be a bit inaccurate, especially for IPv6 (it places some CZ.NIC nameservers in Ukraine etc.).

Using [ODVR](https://blog.nic.cz/2019/04/30/spoustime-nove-odvr/) or other resolvers:

```yaml
dns:
  - 193.17.47.1
  - 185.43.135.1
```

If no resolvers are specified (`dns` is missing or empty in the config file), the crawler will attempt to use system settings (handled by `dnspython`, but it usually ends up with `/etc/resolv.conf` on Linux).

## Command line parameters

### main.py

```
main.py <file>
       file - plaintext domain list, one domain per line (separated by \n)
```

The main process uses threads (2 for each CPU core) to create the jobs faster. It's *much* faster on (more) modern machines – eg. i7-7600U in a laptop does about 4.2k jobs/s, while server with Xeon X3430 does just about 1.4k (using 8 threads, as they both appear as 4 core to the system).

To cancel the process, just send a kill signal or hit `Ctrl-C` any time. The process will perform cleanup and exit.

### workers.py

```
Usage: workers.py [count] [redis]
       count - worker count, 8 workers per CPU core by default
       redis - redis host, localhost:6379 by default

Examples: workers.py 8
          workers.py 24 192.168.0.22:4444
          workers.py 16 redis.foo.bar
```

Trying to use more than 24 workers per CPU core will result in a warning (and countdown before it actually starts the workers):

```
$ workers.py 999
Whoa. You are trying to run 999 workers on 4 CPU cores.
Cancel now (Ctrl-C) or have a fire extinguisher ready.
5 - 4 - 3 -
```

Stopping works the same way as with the main process – `Ctrl-C` (or kill signal) will finish the current job(s) and exit.

> The workers will shout at you that *"Result will never expire, clean up result key manually"*. This is perfectly fine, results are continually cleaned by the main process. Unfortunately there's no easy way to disable this message in `rq` without setting a fixed TTL.

## Resuming work

Stopping the workers won't delete the jobs from Redis. So, if you stop the `workers.py` process and then start a new one (perhaps to use different worker count…), it will pick up the unfinished jobs and continue.

This can also be used change the worker count if it turns out to be too low or hight for your machine or network:

- to reduce the worker count, just stop the `workers.py` process and start a new one with a new count
- to increase the worker count, either use the same approach, or just start a second `workers.py` process in another shell, the worker count will just add up
- scaling to multiple machines works the same way, see below

## Running on multiple machines

Since all communication between the main process and workers is done through Redis, it's easy to scale the crawler to any number of machines:

```
server-1                     server-1
┬──────────────────┐         ┬──────────────────┐
│     main.py      │         │     workers.py   │
│        +         │ ------- │        +         │
│      redis       │         │    DNS resolver  │
└──────────────────┘         └──────────────────┘

                             server-2
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
                    ^            ^
                    24 threads   redis host
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
$ rq-dashboard
RQ Dashboard version 0.4.0                                                 
 * Serving Flask app "rq_dashboard.cli" (lazy loading)                            
 * Environment: production                                                
   WARNING: Do not use the development server in a production environment. 
   Use a production WSGI server instead.                                          
 * Debug mode: off                            
 * Running on http://0.0.0.0:9181/ (Press CTRL+C to quit)
 ```

<a href="https://i.vgy.me/sk7zWa.png">
<img alt="RQ Dashboard screenshot" src="https://i.vgy.me/sk7zWa.png" width="40%">
</a>
<a href="https://i.vgy.me/4y5Zee.png">
<img alt="RQ Dashboard screenshot" src="https://i.vgy.me/4y5Zee.png" width="40%">
</a>

## Tests

Some basic tests are in the `tests` directory in this repo. If you want to run them manually, take a look at the `test` stage jobs in `.gitlab-ci.yml`. Basically it just downloads free GeoIP DBs, tells the crawler to use them, and crawles some domains, checking values in JSON output. It runs the tests twice – first with the default DNS resolvers (ODVR) and then with system one(s).

If you're looking into writing some additional tests, be aware that some Docker containers used in GitLab CI don't have IPv6 configured (even if it's working on the host machine), so checking for eg. `WEB6_80_www_VENDOR` will fail without additional setup.

## Bug reporting

Please create [issues in this Gitlab repo](https://gitlab.labs.nic.cz/adam/dns-crawler/issues).