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

Start Redis. The exact command depends on your system.

Feed domains into queue and wait for results:

```
$ dns-crawler domain-list.txt > result.json
```

(in another shell) Start workers which process the domains and return results to the main process:

```
$ dns-crawler-workers
```

## How fast is it anyway?

A single laptop on ~50Mbps connection can crawl the entire *.cz* zone overnight, give or take (with `save_web_content` disabled).

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

### Trying it out

Create a short domain list (one 2nd level domain per line):

```
$ echo -e "nic.cz\nnetmetr.cz\nroot.cz" > domains.txt
```

Start the main process to create job for every domain:

```
$ dns-crawler domains.txt
[2019-09-24 07:38:15] Reading domains from …/domains.txt.
[2019-09-24 07:38:15] Creating job queue using 2 threads.
[2019-09-24 07:38:15] 0/3 jobs created.
[2019-09-24 07:38:16] 3/3 jobs created.
[2019-09-24 07:38:16] Created 3 jobs. Waiting for workers…
[2019-09-24 07:38:17] 0/3
```

Now it waits for workers to take the jobs from redis. Run a worker in another shell:

```
$ dns-crawler-workers 3
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

#### Formatting the JSON output

If you want formatted JSONs, just pipe the output through [jq](https://stedolan.github.io/jq/): `dns-crawler list.txt | jq`.

#### SQL output

An util to create SQL `INSERT`s from the crawler output is included in this repo.

```
$ dns-crawler list.txt | python output_sql.py table_name
INSERT INTO table_name VALUES …;
INSERT INTO table_name VALUES …;
```

You can even pipe it right into `psql` or another DB client, which will save the results into DB continually, as they come from the workers:

```
$ dns-crawler list.txt | python output_sql.py table_name | psql -d db_name …
```

It can also generate the table structure (`CREATE TABLE …`), taking the table name as a single argument (without piping anything to stdin):

```
$ python output_sql.py results
CREATE TABLE results …;
```

The SQL output is tested only with PostgreSQL 11.

There's also `output_sql.py`, useful for inserting big chunks of resuls (which would be slow to do one by one).

#### Saving to Hadoop

TODO

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

(and then just `dns-crawler domains.txt | python yaml.py`)

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

GeoIP DB paths, DNS resolver IP(s), and timeouts are read from `config.yml` in the working directory, if present.

The default values are:

```yaml
geoip:
  country: /usr/share/GeoIP/GeoIP2-Country.mmdb
  isp: /usr/share/GeoIP/GeoIP2-ISP.mmdb
dns:
  - 127.0.0.1
job_timeout: 80  # max. duration for a single domain (seconds) 
dns_timeout: 2 # seconds
http_timeout: 2 # seconds
save_web_content: False  # beware, setting to True will output HUGE files
strip_html: False # when saving web content, strip HTML tags, scripts, and CSS
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

### dns-crawler

```
dns-crawler <file>
       file - plaintext domain list, one domain per line (separated by \n)
```

The main process uses threads (2 for each CPU core) to create the jobs faster. It's *much* faster on (more) modern machines – eg. i7-7600U in a laptop does about 4.2k jobs/s, while server with Xeon X3430 does just about 1.4k (using 8 threads, as they both appear as 4 core to the system).

To cancel the process, just send a kill signal or hit `Ctrl-C` any time. The process will perform cleanup and exit.

### dns-crawler-workers

```
Usage: dns-crawler-workers [count] [redis]
       count - worker count, 8 workers per CPU core by default
       redis - redis host, localhost:6379 by default

Examples: dns-crawler-workers 8
          dns-crawler-workers 24 192.168.0.22:4444
          dns-crawler-workers 16 redis.foo.bar
```

Trying to use more than 24 workers per CPU core will result in a warning (and countdown before it actually starts the workers):

```
$ dns-crawler-workers 999
Whoa. You are trying to run 999 workers on 4 CPU cores. It's easy toscale
across multiple machines, if you need to. See README.md for details.

Cancel now (Ctrl-C) or have a fire extinguisher ready.
5 - 4 - 3 -
```

Stopping works the same way as with the main process – `Ctrl-C` (or kill signal) will finish the current job(s) and exit.

> The workers will shout at you that *"Result will never expire, clean up result key manually"*. This is perfectly fine, results are continually cleaned by the main process. Unfortunately there's no easy way to disable this message in `rq` without setting a fixed TTL.

## Resuming work

Stopping the workers won't delete the jobs from Redis. So, if you stop the `dns-crawler-workers` process and then start a new one (perhaps to use different worker count…), it will pick up the unfinished jobs and continue.

This can also be used change the worker count if it turns out to be too low or hight for your machine or network:

- to reduce the worker count, just stop the `dns-crawler-workers` process and start a new one with a new count
- to increase the worker count, either use the same approach, or just start a second `dns-crawler-workers` process in another shell, the worker count will just add up
- scaling to multiple machines works the same way, see below

## Running on multiple machines

Since all communication between the main process and workers is done through Redis, it's easy to scale the crawler to any number of machines:

```
machine-1                     machine-1
┬──────────────────┐         ┬────────────────────┐
│    dns-crawler   │         │ dns-crawler-workers│
│        +         │ ------- │          +         │
│      redis       │         │    DNS resolver    │
└──────────────────┘         └────────────────────┘

                             machine-2
                             ┬─────────────────────┐
                             │ dns-crawler-workers │
                     ------- │          +          │
                             │    DNS resolver     │
                             └─────────────────────┘

                             …
                             …

                             machine-n
                             ┬─────────────────────┐
                             │ dns-crawler-workers │
                     _______ │          +          │
                             │    DNS resolver     │
                             └─────────────────────┘
```

Just tell the workers to connect to the shared Redis on the main server, eg.:

```
$ dns-crawler-workers 24 192.168.0.2:6379
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


## OS support

The crawler is developed primarily for Linux, but it should work on any OS supported by Python –at least the worker part (but the main process should work too, if you manage to get a Redis server running on your OS).

One exception is Windows, because it [doesn't support `fork()`](https://github.com/rq/rq/issues/859), but it's possible to get it working under WSL (Windows Subsystem for Linux):

![win10 screenshot](https://i.vgy.me/emJjGN.png)

…so you can turn a gaming machine into an internet crawler quite easily.


## Bug reporting

Please create [issues in this Gitlab repo](https://gitlab.labs.nic.cz/adam/dns-crawler/issues).