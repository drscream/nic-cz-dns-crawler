# `dns-crawler`

> A crawler for getting info about *(possibly a huge number of)* DNS domains

[<img alt="CZ.NIC" src="https://adam.nic.cz/media/filer_public/5f/27/5f274de4-7c39-40b2-9942-ef5e7cb66d12/logo-cznic.svg" height="35">](https://www.nic.cz/)&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
[<img alt="ADAM" src="https://adam.nic.cz/static/img/logo-adam.svg" height="50">](https://adam.nic.cz/)

[![PyPI version shields.io](https://img.shields.io/pypi/v/dns-crawler.svg)](https://pypi.python.org/pypi/dns-crawler/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/dns-crawler.svg)](https://pypi.python.org/pypi/dns-crawler/)
[![PyPI license](https://img.shields.io/pypi/l/dns-crawler.svg)](https://pypi.python.org/pypi/dns-crawler/)
[![PyPI downloads per week](https://img.shields.io/pypi/dm/dns-crawler.svg)](https://pypi.python.org/pypi/dns-crawler/)

# What does it do?

Despite the name, the crawler gets info for more services than just DNS:

- DNS:
  - all A/AAAA records (for the 2nd level domain and `www.` subdomain), optionally annotated with GeoIP
  - TXT records (with SPF and DMARC parsed for easier filtering)
  - TLSA (for the 2nd level domain and `www.` subdomain)
  - MX
  - DNSSEC validation
  - nameservers:
    - each server IP optionally annotated with GeoIP
    - HOSTNAME.BIND, VERSION.BIND, AUTHORS.BIND and fortune (also for all IPs)
  - users can add custom additional RRs in the config file
- E-mail (for every server from MX):
  - SMTP server banners (optional, ports are configurable)
  - TLSA records
- Web:
  - HTTP status & headers (inc. parsed cookies) for ports 80 & 443 on each IP from A/AAAA records
  - certificate info for HTTPS (optionally with an entire cert chain)
  - webpage content (optional)
  - everything of the above is saved for each _step_ in the redirect history – the crawler follows redirects until it gets a non-redirecting status or hits a configurable limit

Answers from name and mail servers are cached, so the crawler shouldn't flood hosting providers with repeating queries.
 
If you need to configure a firewall, the crawler connects to ports `53` (both UDP and TCP), `25` (TCP), `80` (TCP), and `443` (TCP for now, but we might add UDP with HTTP3…).

See [`result-example.json`](https://gitlab.nic.cz/adam/dns-crawler/-/blob/master/result-example.json) to get an idea what the resulting JSON looks like.

## How fast is it anyway?

A single fairly modern laptop on ~50Mbps connection can crawl the entire *.cz* zone (~1.3M second level domains) overnight, give or take, using 8 workers per CPU thread.

Since the crawler is designed to be parallel, the actual speed depends almost entirely on the worker count. And it can scale accross multiple machines almost infinitely, so should you need a million domains crawled in an hour, you can always just throw more hardware at it (see below).

CZ.NIC uses 4 machines in production (8-core Xeon Bronze 3106, 16 GB RAM, gigabit line) and crawling the entire *.cz* zone takes under 3 hours.

## Installation

Create and activate a virtual environment:

```bash
mkdir dns-crawler
cd dns-crawler
python3 -m venv .venv
source .venv/bin/activate
```

Install `dns-crawler`:

```bash
pip install dns-crawler
```

Depending on your OS/distro, you might need to install some system packages. On Debian/Ubuntu, `apt install libicu-dev pkg-config build-essential` should do the trick (assumung you already have python3 installed of course).

## Basic usage

To run a single-threaded crawler (suitable for small domain counts), just pass a domain list:

```
$ echo -e "nic.cz\nnetmetr.cz\nroot.cz" > domain-list.txt
$ dns-crawler domain-list.txt > results.json
[2019-12-03 11:03:54] Reading domains from domain-list.txt.
[2019-12-03 11:03:54] Read 3 domains.
[2019-12-03 11:03:55] 1/3
[2019-12-03 11:03:55] 2/3
[2019-12-03 11:03:56] 3/3
[2019-12-03 11:03:56] Finished.
```

Results are printed to stdout – JSON for every domain, separated by `\n`:

```
$ cat results.json
{"domain": "nic.cz", "timestamp": "2019-12-03 10:03:55", "results": {…}}
{"domain": "netmetr.cz", "timestamp": "2019-12-03 10:03:55", "results": {…}}
{"domain": "root.cz", "timestamp": "2019-12-03 10:03:56", "results": {…}}
```

If you want formatted JSONs, just pipe the output through [jq](https://stedolan.github.io/jq/) or your tool of choice: `dns-crawler domain-list.txt | jq`.

## Multithreaded crawling

First, you need a Redis server running & listening.

The crawler can run with multiple threads to speed things up when you have a lot of domains to go through. Communication betweeen the controller and workers is done through Redis (this makes it easy to run workers on multiple machines if needed, see below).

Start Redis. The exact command depends on your system. If you want to use a different machine for Redis & the crawler controller, see [CLI parameters for dns-crawler-controller](#dns-crawler-controller).

Feed domains into queue and wait for results:

```
$ dns-crawler-controller domain-list.txt > result.json
```

(in another shell) Start workers which process the domains and return results to the controller:

```
$ dns-crawler-workers
```

Using the controller also gives you caching of repeating queries (mailserver banners and hostname.bind/version.bind for nameservers) for free.

### Redis configuration

No special config needed, but increase the memory limit if you have a lot of domains to process (eg. `maxmemory 2G`). You can also disable disk snapshots to save some I/O time (comment out the `save …` lines). If you're not already using Redis for other things, read its log – there are often some recommendations for performance improvements.

## Results

Results are printed to the main process' (`dns-crawler` or `dns-crawler-controller`) stdout – JSON for every domain, separated by `\n`:

```
…
[2019-05-03 07:38:17] 2/3
{"domain": "nic.cz", "timestamp": "2019-09-24T05:28:06.536991", "results": {…}}
…
```

The progress info with timestamp is printed to stderr, so you can save just the output easily – `dns-crawler list.txt > results`.

A JSON schema for the output JSON is included in the repository: [`result-schema.json`](https://gitlab.nic.cz/adam/dns-crawler/-/blob/master/result-schema.json), and also an example for nic.cz: [`result-example.json`](https://gitlab.nic.cz/adam/dns-crawler/-/blob/master/result-example.json).

There are several tools for schema validation, viewing, and even code generation.

To validate a result against schema (CI is set up to do it automatically):

```bash
$ pip install jsonschema
$ jsonschema -i result-example.json result-schema.json # if it prints nothing, it's valid
```

Or, if you don't loathe JS, `ajv` has a much better output:

```bash
$ npm i -g ajv-cli
$ ajv validate -s result-schema.json -d result-example.json
```

### Storing crawler results

In production, CZ.NIC uses Hadoop cluster to store the results file after the crawler run is over – see a script in `utils/crawler-hadoop.sh` (pushes the results file to Hadoop and notifies a Mattermost channel).

You can even pipe the output right to hadoop without even storing it on your disk:

```
dns-crawler-controller domain-list.txt | ssh user@hadoop-node "HADOOP_USER_NAME=… hadoop fs -put - /path/to/results.json;"
```

### Working with the results

- [R package for dns-crawler output processing](https://gitlab.nic.cz/adam/dnscrawler.parser)

## Usage in Python code

Just import and use the `process_domain` function like so:

```
$ python
>>> from dns_crawler.crawl import process_domain
>>> result = process_domain("nic.cz")
>>> result
{'domain': 'nic.cz', 'timestamp': '2019-09-13T09:21:10.136303', 'results': { … 
>>>
>>> result["results"]["DNS_LOCAL"]["DNS_AUTH"]
[{'value': 'a.ns.nic.cz.'}, {'value': 'b.ns.nic.cz.'}, {'value': 'd.ns.nic.cz.'}]
```

The `process_domain` function returns Python `dict`s. If you want json, use `from dns_crawler.crawl import get_json_result` instead:

```
$ python
>>> from dns_crawler.crawl import get_json_result
>>> result = get_json_result("nic.cz")
>>> result
# same as above, just converted to JSON
```

This function just calls `crawl_domain` and converts the `dict` to JSON string. It's used by the workers, so the conversion is done by them to take some pressure off the controller process.


## Config file

GeoIP DB paths, DNS resolver IP(s), timeouts, and bunch of other things are read from `config.yml` in the working directory, if present.

The default values are listed in [`config.yml`](https://gitlab.nic.cz/adam/dns-crawler/-/blob/master/config.yml) with explanatory comments.

If you're using the multi-threaded crawler (`dns-crawler-controller` & `dns-crawler-workers`), the config is loaded by the controlled and shared with the workers via Redis.

You can override it on the worker machines if needed – just create a `config.yml` in their working dir (eg. to set different resolver IP(s) or GeoIP paths on each machine). The config is then merged – directives not defined in the worker config are loaded from the controller one (and defaults are used if the're not defined there either). But – depending on values you change – you might then get a different results from each worker machine of course.


### GeoIP annotation

For this to work, you need to get GeoIP databases for the crawler to use. It supports both paid and free ones ([can be downloaded here after registration](https://dev.maxmind.com/geoip/geoip2/geolite2/)).

The crawler expects them in `/usr/share/GeoIP` (Maxmind's [geoipupdate](https://github.com/maxmind/geoipupdate) places them there by default), but that can be easily changed in a config file:

```yaml
geoip:
  enabled: True
  country: /path/to/GeoLite2-Country.mmdb
  asn: /path/to/GeoLite2-ASN.mmdb
```

Using commercial (GeoIP2 Country and ISP) DBs instead of free (GeoLite2 Country and ASN) ones:

```yaml
geoip:
  enabled: True
  country: /usr/share/GeoIP/GeoLite2-Country.mmdb
  #  asn: /usr/share/GeoIP/GeoLite2-ASN.mmdb  # 'asn' is the free DB
  isp: /usr/share/GeoIP/GeoIP2-ISP.mmdb  # 'isp' is the commercial one
```

(use either absolute paths or relative to the working directory)

`ISP` (paid) database is preferred over `ASN` (free), if both are defined. The difference is described on Maxmind's website: https://dev.maxmind.com/faq/what-is-the-difference-between-the-geoip-isp-and-organization-databases/.

The free `GeoLite2-Country` seems to be a bit inaccurate, especially for IPv6 (it places some CZ.NIC nameservers in Ukraine etc.).

### Getting additional DNS resource records:

You can easily get some additional RRs (for the 2nd level domain) which aren't included in the crawler by default:

```yaml
dns:
  additional:
    - SPF
    - CAA
    - CERT
    - LOC
    - SSHFP
```

See the [List of DNS record types](https://en.wikipedia.org/wiki/List_of_DNS_record_types) for some ideas. Things like OPENPGPKEY won't work though, because they are intented to be used on a subdomain (generated as a hash of part of e-mail address in this case).

You can plug a parser for the record by adding a function to the `additional_parsers` enum in `dns_utils.py`. The only one included by default is SPF (since the deprecated SPF record has the same format as SPF from TXT which the crawler is getting by default).

## Command line parameters

### dns-crawler

```
dns-crawler - a single-threaded crawler to process a small number of domains without a need for Redis

Usage: dns-crawler <file>
       file - plaintext domain list, one domain per line, empty lines are ignored
```

### dns-crawler-controller

```
dns-crawler-controller - the main process controlling the job queue and printing results.

Usage: dns-crawler-controller <file> [redis]
       file - plaintext domain list, one domain per line, empty lines are ignored
       redis - redis host:port:db, localhost:6379:0 by default

Examples: dns-crawler-controller domains.txt
          dns-crawler-controller domains.txt 192.168.0.22:4444:0
          dns-crawler-controller domains.txt redis.foo.bar:7777:2
          dns-crawler-controller domains.txt redis.foo.bar # port 6379 and DB 0 will be used if not specified
```

The controller process uses threads (4 for each CPU core) to create the jobs faster when you give it a lot of domains (>1000× CPU core count).

It's *much* faster on (more) modern machines – eg. i7-7600U (with HT) in a laptop does about 19k jobs/s, while server with Xeon X3430 (without HT) does just about ~7k (both using 16 threads, as they both appear as 4 core to the system).

To cancel the process, just send a kill signal or hit `Ctrl-C` any time. The process will perform cleanup and exit.

### dns-crawler-workers

```
dns-crawler-workers - a process that spawns crawler workers.

Usage: dns-crawler-workers [count] [redis]
       count - worker count, 8 workers per CPU core by default
       redis - redis host:port:db, localhost:6379:0 by default

Examples: dns-crawler-workers 8
          dns-crawler-workers 24 192.168.0.22:4444:0
          dns-crawler-workers 16 redis.foo.bar:7777:2
          dns-crawler-workers 16 redis.foo.bar # port 6379 and DB 0 will be used if not specified
```

Trying to use more than 24 workers per CPU core will result in a warning (and countdown before it actually starts the workers):

```
$ dns-crawler-workers 999
Whoa. You are trying to run 999 workers on 4 CPU cores. It's easy toscale
across multiple machines, if you need to. See README.md for details.

Cancel now (Ctrl-C) or have a fire extinguisher ready.
5 - 4 - 3 -
```

Stopping works the same way as with the controller process – `Ctrl-C` (or kill signal) will finish the current job(s) and exit.

## Resuming work

Stopping the workers won't delete the jobs from Redis. So, if you stop the `dns-crawler-workers` process and then start a new one (perhaps to use different worker count…), it will pick up the unfinished jobs and continue.

This can also be used change the worker count if it turns out to be too low or high for your machine or network:

- to reduce the worker count, just stop the `dns-crawler-workers` process and start a new one with a new count
- to increase the worker count, either use the same approach, or just start a second `dns-crawler-workers` process in another shell, the worker count will just add up
- scaling to multiple machines works the same way, see below

## Running on multiple machines

Since all communication between the controller and workers is done through Redis, it's easy to scale the crawler to any number of machines:

```
machine-1                     machine-1
┬───────────────────────────┐         ┬─────────────────────┐
│    dns-crawler-controller │ ------- │ dns-crawler-workers │
│             +             │         └─────────────────────┘
│           redis           │
│             +             │
│        DNS resolver       │
└───────────────────────────┘
                                      machine-2
                                      ┬─────────────────────┐
                              ------- │ dns-crawler-workers │
                                      └─────────────────────┘
                                      …
                                      …

                                      machine-n
                                      ┬─────────────────────┐
                              _______ │ dns-crawler-workers │
                                      └─────────────────────┘
```

Just tell the workers to connect to the shared Redis on the main server, eg.:

```
$ dns-crawler-workers 24 192.168.0.2:6379
                    ^            ^
                    24 threads   redis host
```

Make sure to run the workers with ~same Python version on these machines, otherwise you'll get `unsupported pickle protocol` errors. See the [pickle protocol versions in Python docs](https://docs.python.org/3.8/library/pickle.html#data-stream-format).

The DNS resolver doesn't have to be on a same machine as the `dns-crawler-controller`, of course – just set it's IP in `config.yml`. The crawler is tested primarily with CZ.NIC's [Knot Resolver](https://www.knot-resolver.cz/), but should work with any sane resolver supporting DNSSEC. Systemd's `systemd-resolved` seems to be really slow though.

Same goes for Redis, you can point both controller and workers to a separate machine running Redis (don't forget to point them to an empty DB if you're using Redis for other things than the dns-crawler, it uses `0` by default).

## Updating dependencies

MaxMind updates GeoIP DBs on Tuesdays, so it may be a good idea to set a cron job to keep them fresh. More about that on [maxmind.com: Automatic Updates for GeoIP2](https://dev.maxmind.com/geoip/geoipupdate/).

If you use multiple machines to run the workers, don't forget to update GeoIP on all of them (or set up a shared location, eg. via sshfs or nfs).

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


## OS support

The crawler is developed primarily for Linux, but it should work on any OS supported by Python – at least the worker part (but the controller should work too, if you manage to get a Redis server running on your OS).

One exception is Windows, because it [doesn't support `fork()`](https://github.com/rq/rq/issues/859), but it's possible to get it working under WSL (Windows Subsystem for Linux):

![win10 screenshot](https://i.vgy.me/emJjGN.png)

…so you can turn a gaming machine into an internet crawler quite easily.


## Bug reporting

Please create [issues in this Gitlab repo](https://gitlab.nic.cz/adam/dns-crawler/issues).