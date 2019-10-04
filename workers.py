import sys
from multiprocessing import cpu_count
import subprocess
from socket import gethostname
from time import sleep
from redis import Redis
from timestamp import timestamp


cpu_count = cpu_count()
worker_count = cpu_count * 8
hostname = gethostname()
redis_host = "localhost:6379"


def print_help():
    sys.stderr.write(f"Usage: {sys.argv[0]} [count] [redis]\n")
    sys.stderr.write(f"       count - worker count, 8 workers per CPU core by default\n")
    sys.stderr.write(f"       redis - redis host, localhost:6379 by default\n\n")
    sys.stderr.write(f"Examples: {sys.argv[0]} 8\n")
    sys.stderr.write(f"          {sys.argv[0]} 24 192.168.0.22:4444\n")
    sys.stderr.write(f"          {sys.argv[0]} 16 redis.foo.bar\n")
    sys.exit(1)


if "-h" in sys.argv or "--help" in sys.argv:
    print_help()


try:
    worker_count = int(sys.argv[1])
except ValueError:
    sys.stderr.write(f"Worker count ('{sys.argv[1]}') is not an integer.\n\n")
    print_help()
except IndexError:
    pass
if worker_count <= 0:
    sys.stderr.write(f"At least one worker is needed.\n\n")
    print_help()
if worker_count > 24 * cpu_count:
    sys.stderr.write((
        f"Whoa. You are trying to run {worker_count} workers on {cpu_count} CPU "
        f"core{('s' if cpu_count > 1 else '')}. It's easy to scale \n"
        f"across multiple machines, if you need to. See README.md for details.\n"
        f"Cancel now (Ctrl-C) or have a fire extinguisher ready.\n")
    )
    try:
        for s in reversed(range(0, 5)):
            sleep(1)
            sys.stdout.write(f"{str(s+1)} - ")
            sys.stdout.flush()
            if s == 0:
                sleep(1)
                sys.stdout.write("ignition")
                print("\n")
    except KeyboardInterrupt:
        sys.exit(1)

if len(sys.argv) > 2:
    redis_host = sys.argv[2]

redis = Redis(host=redis_host.split(":")[0], port=redis_host.split(":")[1])
commands = []

for n in range(worker_count):
    commands += [["rq", "worker", "--burst", "-n", f"{hostname}-{n+1}", "-u", f"redis://{redis_host}"]]

while redis.get("locked") == b"1":
    sys.stderr.write(f"{timestamp()} Waiting for the main process to unlock the queue.\n")
    sleep(5)

procs = [subprocess.Popen(i) for i in commands]

try:
    for p in procs:
        p.wait()
except KeyboardInterrupt:
    pass
