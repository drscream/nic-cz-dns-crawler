<img alt="CZ.NIC" src="https://www.nic.cz/static/www.nic.cz/images/logo_en.png" align="right" /><br/><br/>

# `dns-crawler`

> A crawler for getting info about *(possibly a huge number of)* DNS domains

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

This is enough to make the crawler work, but you will probably get `AttributeError: module 'dns.message' has no attribute 'Truncated'` for a lot of domains. This is because the crawler uses current `dnspython`, but the last release on PyPI is ages behind the current code. It can be fixed easily just by installing `dnspython` from git:

```bash
pip install -U git+https://github.com/rthalley/dnspython.git
```

(PyPI [doesn't allow us](https://github.com/pypa/pip/issues/6301) to specify the git url it in dependencies unfortunately)

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

The crawler can run with multiple threads to speed things up when you have a lot of domains to go through. Communication betweeen the controller and workers is done through Redis (this makes it easy to run workers on multiple machines if needed, see below).

Start Redis. The exact command depends on your system.

Feed domains into queue and wait for results:

```
$ dns-crawler-controller domain-list.txt > result.json
```

(in another shell) Start workers which process the domains and return results to the controller:

```
$ dns-crawler-workers
```

## How fast is it anyway?

A single fairly modern laptop on ~50Mbps connection can crawl the entire *.cz* zone overnight, give or take (with `save_web_content` disabled), using 8 workers per CPU thread.

Since the crawler is designed to be parallel, the actual speed depends almost entirely on the worker count. And it can scale accross multiple machines almost infinitely, so should you need a million domains crawled in an hour, you can always just throw more hardware at it.

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

### Output formats

Results are printed to the main process' (`dns-crawler` or `dns-crawler-controller`) stdout – JSON for every domain, separated by `\n`:

```
…
[2019-05-03 07:38:17] 2/3
{"domain": "nic.cz", "timestamp": "2019-09-24T05:28:06.536991", "results": {…}}
…
```

The progress info with timestamp is printed to stderr, so you can save just the output easily – `dns-crawler list.txt > results`.

A JSON schema for the output JSON is included in this repository: [`result-schema.json`](result-schema.json), and also an example for nic.cz: [`result-example.json`](result-example.json).

There are several tools for schema validation, viewing, and even code generation.

To validate a result against schema (CI is set up to do it automatically):

```bash
$ pip install jsonschema
$ jsonschema -i result-example.json result-schema.json # if it prints nothing, it's valid
```

Or, if you don't loathe JS, `ajv` has a much better output:

```bash
$ npm i -g ajv
$ ajv validate -s result-schema.json -d result-example.json
```

#### Custom output format

Since the main process (`dns-crawler` or `dns-crawler-controller`) just spits out JSONs to stdout, it's pretty easy to process it with almost anything.

A simple example for YAML output:

```python
import json
import yaml
import sys

for line in sys.stdin:
    print(yaml.dump(json.loads(line)))
```

(and then just `dns-crawler domains.txt | python yaml.py`)

CSV is a different beast, since there's no obvious way to represent arrays…

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

Formatted output, inline python code:

```
$ python -c "from dns_crawler.crawl import process_domain; import json; print(json.dumps(process_domain('nic.cz'), indent=2))"
{
  "domain": "nic.cz",
  "timestamp": "2019-09-13T09:24:23.108941",
  "results": {
    "DNS_LOCAL": {
      "DNS_AUTH": [
        …
```


## Config file

GeoIP DB paths, DNS resolver IP(s), and timeouts are read from `config.yml` in the working directory, if present.

The default values are:

```yaml
geoip:
  country: /usr/share/GeoIP/GeoIP2-Country.mmdb
  isp: /usr/share/GeoIP/GeoIP2-ISP.mmdb
dns:
  - 193.17.47.1  # https://www.nic.cz/odvr/
job_timeout: 80  # max. duration for a single domain (seconds) 
dns_timeout: 2  # seconds
http_timeout: 2  # seconds
save_web_content: False  # beware, setting to True will output HUGE files
strip_html: True  # when saving web content, strip HTML tags, scripts, and CSS
```

Using free (GeoLite2) Country and ASN DBs instead of commercial ones:

```yaml
geoip:
  country: /usr/share/GeoIP/GeoLite2-Country.mmdb
  asn: /usr/share/GeoIP/GeoLite2-ASN.mmdb
```

(use either absolute paths or relative to the working directory)

`ISP` (paid) database is preferred over `ASN` (free), if both are defined. The difference is described on Maxmind's website: https://dev.maxmind.com/faq/what-is-the-difference-between-the-geoip-isp-and-organization-databases/.

The free `GeoLite2-Country` seems to be a bit inaccurate, especially for IPv6 (it places some CZ.NIC nameservers in Ukraine etc.).

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

It's *much* faster on (more) modern machines – eg. i7-7600U (with HT) in a laptop does about 97k jobs/s, while server with Xeon X3430 (without HT) does just about ~7k (both using 16 threads, as they both appear as 4 core to the system).

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

The DNS resolver doesn't have to be on a same machine as the `dns-crawler-controller`, of course – just set it's IP in `config.yml`. Same goes for Redis, you can point both controller and workers to a separate machine running Redis (don't forget to point them to an empty DB if you're using Redis for other things than the dns-crawler).

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

Please create [issues in this Gitlab repo](https://gitlab.labs.nic.cz/adam/dns-crawler/issues).