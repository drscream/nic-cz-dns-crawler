# `dns-crawler`

> Crawler for getting info about a huge number of DNS domains


## Installation

### Requirements

- Python 3.6+
- [rq](https://python-rq.org/)
- [redis](https://redis.io/)
- [requests](https://python-requests.org/)
- [dnspython](http://www.dnspython.org/)
- [geoip2](https://geoip2.readthedocs.io/en/latest/) + up-to-date Country and ISP databases (mmdb format)
- local DNS resolver (tested with Knot Resolver only, but it shouldn't matter)

### Redis confinguration

- increase memory limit if you have a lot of domains to process (`maxmemory 1G`)
- you can disable disk snapshots to save some I/O time (comment out `save …` lines)

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

Results are printed to the main process' stdout – JSON for every domain, separated by `\n`.

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

